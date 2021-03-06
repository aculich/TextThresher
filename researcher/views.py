import logging
logger = logging.getLogger(__name__)
import tarfile, tempfile

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Min, Max

from researcher.forms import UploadArticlesForm, UploadSchemaForm
from researcher.forms import SendTasksForm

from data.document_importer import import_archive
from data.schema_importer import import_schema

from data.pybossa_api import create_or_update_remote_project, delete_remote_project
from data.pybossa_api import generate_highlight_tasks_worker
from data.pybossa_api import generate_quiz_tasks_worker
from data.pybossa_api import generate_get_taskruns_worker
from data.nlp_exporter import generate_nlp_tasks_worker
from data.pybossa_api import InvalidTaskType
from thresher.models import Article, Topic, UserProfile, Project

class IndexView(TemplateView):
    template_name = 'researcher/index.html'

    def get(self, request):
        # We need 'request' in the context so use render
        return render(request,
                      self.template_name,
                      {'projects': Project.objects.filter(pybossa_id__isnull=False).order_by('name')}
        )

class UploadArticlesView(PermissionRequiredMixin, View):
    form_class = UploadArticlesForm
    template_name = 'researcher/upload_article_form.html'
    login_url = reverse_lazy('admin:login')
    redirect_field_name = 'next'
    permission_required = u'thresher.add_article'

    def get(self, request):
        return render(
            request,
            self.template_name,
            {'form': self.form_class()}
        )

    def post(self, request):
        bound_form = self.form_class(request.POST, request.FILES)
        if bound_form.is_valid():
            f = request.FILES['article_archive_file']
            with_annotations = bound_form.cleaned_data["with_annotations"]
            logger.info("Request to import article archive %s, length %d" % (f.name, f.size))
            with tempfile.NamedTemporaryFile(delete=False) as archive_file:
                for chunk in f.chunks():
                    archive_file.write(chunk)
                archive_file.flush()
                logger.info("Archive copied to temp file %s: tar file format: %s"
                            % (archive_file.name, tarfile.is_tarfile(archive_file.name)))
                import_archive(archive_file.name, request.user.userprofile.id, with_annotations)

            return redirect('/admin/thresher/article/')
        else:
            return render(
                request,
                self.template_name,
                {'form': bound_form}
            )

class UploadSchemaView(PermissionRequiredMixin, View):
    form_class = UploadSchemaForm
    template_name = 'researcher/upload_schema_form.html'
    login_url = reverse_lazy('admin:login')
    redirect_field_name = 'next'
    permission_required = (
        u'thresher.add_topic',
        u'thresher.add_question',
        u'thresher.add_answer',
    )

    def get(self, request):
        return render(
            request,
            self.template_name,
            {'form': self.form_class()}
        )

    def post(self, request):
        bound_form = self.form_class(request.POST, request.FILES)
        if bound_form.is_valid():
            f = request.FILES['schema_file']
            logger.info("Request to import schema %s, length %d" % (f.name, f.size))
            with tempfile.NamedTemporaryFile(delete=True) as schema_file:
                for chunk in f.chunks():
                    schema_file.write(chunk)
                logger.info("Schema copied to temp file %s" % schema_file.name)
                schema_file.seek(0)
                schema_contents = schema_file.read()
                import_schema.delay(schema_contents, request.user.userprofile.id)

            return redirect('/admin/thresher/topic/')
        else:
            return render(
                request,
                self.template_name,
                {'form': bound_form}
            )

class SendTasksView(PermissionRequiredMixin, View):
    form_class = SendTasksForm
    template_name = 'researcher/send_tasks.html'
    login_url = reverse_lazy('admin:login')
    redirect_field_name = 'next'
    # We are creating remotely, so real permission is via Pybossa API key.
    # Put some requirements on form access.
    permission_required = (
        u'thresher.add_project',
        u'thresher.change_project',
        u'thresher.add_task',
        u'thresher.change_task',
    )

    def get_task_generator(self, project):
        if project.task_type == 'HLTR':
            return generate_highlight_tasks_worker.delay
        elif project.task_type == 'QUIZ':
            return generate_quiz_tasks_worker.delay
        else:
            raise InvalidTaskType("Project task type must be 'HLTR' or 'QUIZ'")

    def get(self, request):
        agg = Article.objects.aggregate(Min('id'), Max('id'))
        initial = { 'starting_article_id': agg['id__min'],
                    'ending_article_id': agg['id__max'],
                    'debug_presenter': request.GET.get("debugPresenter", False)
        }
        return render(
            request,
            self.template_name,
            {'form': self.form_class(initial=initial),
             'user': request.user,
            }
        )

    def post(self, request):
        bound_form = self.form_class(request.POST)
        if request.user.is_authenticated and bound_form.is_valid():
            profile_id = request.user.userprofile.id

            starting_article_id = bound_form.cleaned_data['starting_article_id']
            ending_article_id = bound_form.cleaned_data['ending_article_id']
            articles = Article.objects.filter(
                id__gte=starting_article_id,
                id__lte=ending_article_id
            ).order_by("id")
            article_ids = list(articles.values_list('id', flat=True))
            logger.info("%d articles in selected range" % len(article_ids))

            topic_ids = list(bound_form.cleaned_data['topics']
                             .values_list('id', flat=True))
            logger.info("%d topics selected" % len(topic_ids))

            project = bound_form.cleaned_data['project']
            project_id = project.id
            job = None
            if bound_form.cleaned_data['add_nlp_hints']:
                generator = generate_nlp_tasks_worker.delay
            else:
                debug_presenter = bound_form.cleaned_data['debug_presenter']
                debug_server = bound_form.cleaned_data['debug_server']
                job = create_or_update_remote_project(request.user.userprofile,
                                                      project,
                                                      debug_presenter=debug_presenter,
                                                      debug_server=debug_server)
                generator = self.get_task_generator(project)

            generator(profile_id=profile_id,
                      article_ids=article_ids,
                      topic_ids=topic_ids,
                      project_id=project_id,
                      depends_on = job)

            return redirect(reverse('rq_home'))
        else:
            return render(
                request,
                self.template_name,
                {'form': self.form_class(),
                 'user': request.user
                }
            )

class RetrieveTaskrunsView(PermissionRequiredMixin, View):
    form_class = SendTasksForm
    template_name = 'researcher/retrieve_taskruns.html'
    login_url = reverse_lazy('admin:login')
    redirect_field_name = 'next'
    # Put a basic requirement on form access.
    permission_required = (
        u'thresher.add_articlehighlight',
        u'thresher.change_articlehighlight',
        u'thresher.delete_articlehighlight',
        u'thresher.add_highlightgroup',
        u'thresher.change_highlightgroup',
        u'thresher.delete_highlightgroup',
     )
    
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        return render(request, self.template_name, {'project': project})

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        job = generate_get_taskruns_worker.delay(request.user.userprofile.id, project.id)
        return redirect(reverse('rq_home'))


class RemoteProjectDeleteView(PermissionRequiredMixin, View):
    form_class = SendTasksForm
    template_name = 'researcher/confirm_remote_project_delete.html'
    login_url = reverse_lazy('admin:login')
    redirect_field_name = 'next'
    # We are deleting remotely, so correct Pybossa API key must be set
    # Put a basic requirement on form access.
    permission_required = ( u'thresher.delete_project',
                            u'thresher.delete_task')

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        return render(request, self.template_name, {'project': project})

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        job = delete_remote_project(request.user.userprofile, project)
        return redirect('researcher:index')
