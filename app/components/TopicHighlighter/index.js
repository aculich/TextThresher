import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import ReactCSSTransitionsGroup from 'react-addons-css-transition-group';

import { colors } from 'utils/colors';
import HighlightTool from 'components/HighlightTool';
import { TopicPicker, TopicInstruction }  from 'components/TopicPicker';
import Project from 'components/Project';

import { styles } from './styles.scss';

const style = require('intro.js/introjs.css');
import { introJs } from 'intro.js/intro.js';

// Two different strategies - the topic picker has additional classnames attached
// so that we can apply the sass variable $pybossa-header-height
// The second one gets a dynamic style since just need to change 'position'
var scrollStyles = {
  'topicFixed': 'topic-picker-fixed',
  'topicAbsolute': 'topic-picker-absolute',
  'instrFixed': {
    position: 'fixed'
  },
  'instrAbsolute': {
    position: 'absolute'
  }
};

export class TopicHighlighter extends Component {
  constructor(props) {
    super(props);
    this.handleScroll = this.handleScroll.bind(this);
    this.state = {
      instrStyle: scrollStyles.instrFixed,
      topicStyle: scrollStyles.topicFixed
    };
  }

  componentDidMount() {
    window.addEventListener('scroll', this.handleScroll);
    var steps = [
      {
        'element': '#article-container',
        'intro': 'Thank you for joining the project! Before you start, skim through the text provided -- you\'ll sort it into different topics later.',
      },
      {
        'element': '.topic-picker-wrapper',
        'intro': 'Now, look at these tabs on the left and read through the topic descriptions. These describe what you will be looking for in the text.',
        'position': 'right',
      },
      {
        'element': '.instructions',
        'intro': 'Here are some more detailed instructions about each topic. Currently, it\'s describing more about the first selected topic.',
        'position': 'top',
      },
      {
        'element': '#article-container',
        'intro': 'Then, we return to the article! Highlight the places in the article that fall into the first topic.',
        'position': 'left',
      },
      {
        'element': '.topic-picker-wrapper',
        'intro': 'When you are finished highlighting text about the first topic, move onto the second topic. (You can always return to previous topics if you come across more relevant words or phrases -- just click on the topic tab and continue highlighting.) Remember: each topic has its own color highlighter, so be sure that the you are highlighting text in the corresponding color for each topic.',
        'position': 'right',
      },
      {
        'element': '#article-container',
        'intro': 'Repeat this process for every remaining topic.',
        'position': 'left',
      },
      {
        'element': '.save-and-next',
        'intro': 'When you’re finished, take a minute to scan your work and ensure that you’ve highlighted all the relevant pieces of text in each topic’s corresponding color. Add and remove highlighting as necessary before pressing "Save and next" to submit your work. Thank you for your contribution to this project!',
        'position': 'left',
      },
    ];

    var intro = introJs();
    intro.setOptions({ 'steps': steps, 'overlayOpacity': 0.5 });
    intro.start();
  }

  componentWillUnmount() {
    window.removeEventListener('scroll', this.handleScroll);
  }

  // The idea here is to handle all the dynamic layout in this
  // component, rather than jamming code specific to this layout
  // down into the called components.
  handleScroll() {
    let navbar = document.querySelector('.navbar');
    let footer = document.querySelector('footer');
    let topicPicker = document.querySelector('.topic-picker-wrapper');
    let getRect = (el) => el.getBoundingClientRect();
    let footerTop = getRect(footer).top;

    // Check if topic picker should start scrolling
    if (footerTop - 1 < getRect(topicPicker).bottom) {
      this.setState({ topicStyle: scrollStyles.topicAbsolute});
    };
    // Check if topic picker should stop scrolling
    if (getRect(topicPicker).top > getRect(navbar).height) {
      this.setState({ topicStyle: scrollStyles.topicFixed});
    };

    // Check if instructions block should start scrolling up
    if (footerTop < window.innerHeight) {
      this.setState({ instrStyle: scrollStyles.instrAbsolute });
    } else {
      this.setState({ instrStyle: scrollStyles.instrFixed });
    };
  }

  // Babel plugin transform-class-properties allows us to use
  // ES2016 property initializer syntax. So the arrow function
  // will bind 'this' of the class. (React.createClass does automatically.)
  onSaveAndNext = () => {
    window.scrollTo(0, 0);
    this.props.saveAndNext(this.props.highlights);
    this.props.clearHighlights();
  }

  render() {
    // TODO: Detect if done
    // return (<div>DONE</div>)

    let loadingClass = this.props.article.isFetching ? 'loading' : '';

    return (
      <ReactCSSTransitionsGroup transitionName='fadein'
                                transitionAppear
                                transitionAppearTimeout={500}
                                transitionEnterTimeout={500}
                                transitionLeaveTimeout={500}>
        <div className={loadingClass}></div>

        <div className='topic-highlighter-wrapper'>
            <TopicPicker
              topics={this.props.topics}
              topicStyle={this.state.topicStyle}
            />
            <ReactCSSTransitionsGroup transitionName='fade-between'
                                      transitionAppear
                                      transitionAppearTimeout={500}
                                      transitionEnterTimeout={500}
                                      transitionLeaveTimeout={500}>
              <div className="article" key={this.props.article.articleId}>
                <Project />
                <div id='article-container'>

                  <HighlightTool
                    text={this.props.article.text}
                    topics={this.props.topics.results}
                    colors={colors}
                    currentTopicId={this.props.currentTopicId}
                  />
                  
                </div>
                <button onClick={this.onSaveAndNext} className='save-and-next'>Save and Next</button>
              </div>
            </ReactCSSTransitionsGroup>
            <TopicInstruction instrStyle={this.state.instrStyle} />
        </div>
      </ReactCSSTransitionsGroup>
    );
  }
};
