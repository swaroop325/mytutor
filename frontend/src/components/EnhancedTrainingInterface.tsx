/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  MessageCircle,
  CheckCircle,
  XCircle,
  Target,
  Trophy,
  ArrowRight,
  BookOpen,
  Lightbulb,
  Play,
  PauseCircle,
  FileText} from 'lucide-react';
import { API_URL } from '../services/api';

interface TrainingQuestion {
  id: number;
  type: 'mcq' | 'open_ended' | 'fill_blank' | 'match' | 'true_false' | 'scenario';
  question: string;
  options?: string[] | Record<string, string>; // Can be array or object {"A": "...", "B": "..."}
  correct_answer: any;
  explanation: string;
  difficulty: string;
  topic: string;
  learning_objective: string;
  estimated_time: number;

  // Additional fields for different question types
  left_column?: string[];
  right_column?: string[];
  correct_matches?: Record<string, string>;
  sample_answer?: string;
  assessment_rubric?: string;
  context_clues?: string;
  scenario_context?: string;
  key_considerations?: string[];
}

interface LearningContent {
  summary: string;
  key_concepts: string[];
  learning_objectives: string[];
}

interface EnhancedTrainingInterfaceProps {
  knowledgeBaseId: string;
  onEndTraining: () => void;
}

export const EnhancedTrainingInterface: React.FC<EnhancedTrainingInterfaceProps> = ({
  knowledgeBaseId,
  onEndTraining
}) => {
  const [phase, setPhase] = useState<'learning' | 'assessment'>('learning');
  const [learningContent, setLearningContent] = useState<LearningContent | null>(null);
  const [session, setSession] = useState<any>(null);
  const [currentQuestion, setCurrentQuestion] = useState<TrainingQuestion | null>(null);
  const [userAnswer, setUserAnswer] = useState<any>('');
  const [showResult, setShowResult] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isStartingAssessment, setIsStartingAssessment] = useState(false);
  const [error, setError] = useState('');
  const [studyTime, setStudyTime] = useState(0);
  const [isStudying, setIsStudying] = useState(false);
  const sessionStartedRef = useRef(false);
  const studyTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (sessionStartedRef.current) return;
    sessionStartedRef.current = true;
    loadLearningContent();
  }, [knowledgeBaseId]);

  useEffect(() => {
    if (isStudying) {
      studyTimerRef.current = setInterval(() => {
        setStudyTime(prev => prev + 1);
      }, 1000);
    } else {
      if (studyTimerRef.current) {
        clearInterval(studyTimerRef.current);
      }
    }

    return () => {
      if (studyTimerRef.current) {
        clearInterval(studyTimerRef.current);
      }
    };
  }, [isStudying]);

  const loadLearningContent = async () => {
    try {
      const response = await fetch(`${API_URL}/knowledge-base/${knowledgeBaseId}/learning-content`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load learning content');
      }

      const content = await response.json();
      setLearningContent(content);
      setLoading(false);
      setIsStudying(true);

    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const startAssessment = async () => {
    try {
      setIsStudying(false);
      setIsStartingAssessment(true);
      setError('');

      const response = await fetch(`${API_URL}/knowledge-base/training/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          knowledge_base_id: knowledgeBaseId,
          question_types: ['mcq', 'open_ended', 'fill_blank', 'match', 'true_false'],
          study_time: studyTime
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start assessment');
      }

      const sessionData = await response.json();
      setSession(sessionData);
      setCurrentQuestion(sessionData.current_question);
      setPhase('assessment');

    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsStartingAssessment(false);
    }
  };

  const submitAnswer = async () => {
    if (!session || !currentQuestion) return;

    // Validate answer based on question type
    if (!validateAnswer()) return;

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/knowledge-base/training/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          session_id: session.id,
          answer: userAnswer,
          question_type: currentQuestion.type
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit answer');
      }

      const result = await response.json();
      setLastResult(result);
      setShowResult(true);
      
      setSession((prev: any) => ({
        ...prev,
        questions_answered: result.questions_answered,
        correct_answers: prev.correct_answers + (result.correct ? 1 : 0),
        score: result.score
      }));

    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const validateAnswer = (): boolean => {
    if (!currentQuestion) return false;

    switch (currentQuestion.type) {
      case 'mcq':
      case 'true_false':
        return userAnswer !== '';
      case 'fill_blank':
      case 'open_ended':
      case 'scenario':
        return typeof userAnswer === 'string' && userAnswer.trim().length > 0;
      case 'match':
        return Object.keys(userAnswer || {}).length > 0;
      default:
        return false;
    }
  };

  const nextQuestion = () => {
    if (lastResult?.next_question) {
      setCurrentQuestion(lastResult.next_question);
      setUserAnswer('');
      setShowResult(false);
      setLastResult(null);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderQuestionInput = () => {
    if (!currentQuestion) return null;

    switch (currentQuestion.type) {
      case 'mcq':
        // Handle both array and object formats for options
        { const options = currentQuestion.options;
        const optionEntries = Array.isArray(options)
          ? options.map((opt, idx) => [String.fromCharCode(65 + idx), opt])
          : Object.entries(options || {});

        return (
          <div className="space-y-3">
            {optionEntries.map(([optionKey, optionText]) => {
              return (
                <motion.button
                  key={optionKey}
                  onClick={() => setUserAnswer(optionKey)}
                  className={`w-full text-left p-4 rounded-lg border transition-all ${
                    userAnswer === optionKey
                      ? 'bg-blue-500/20 border-blue-500/50 text-white'
                      : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10 hover:border-white/20'
                  }`}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-bold ${
                      userAnswer === optionKey
                        ? 'border-blue-400 bg-blue-500/30 text-blue-200'
                        : 'border-white/30 text-white/60'
                    }`}>
                      {optionKey}
                    </div>
                    <span>{optionText}</span>
                  </div>
                </motion.button>
              );
            })}
          </div>
        ); }

      case 'true_false':
        return (
          <div className="flex gap-4">
            {['true', 'false'].map((option) => (
              <motion.button
                key={option}
                onClick={() => setUserAnswer(option)}
                className={`flex-1 p-6 rounded-lg border transition-all ${
                  userAnswer === option
                    ? 'bg-blue-500/20 border-blue-500/50 text-white'
                    : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10'
                }`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <div className="flex items-center justify-center gap-3">
                  {option === 'true' ? (
                    <CheckCircle className="w-8 h-8 text-green-400" />
                  ) : (
                    <XCircle className="w-8 h-8 text-red-400" />
                  )}
                  <span className="text-xl font-semibold capitalize">{option}</span>
                </div>
              </motion.button>
            ))}
          </div>
        );

      case 'fill_blank':
        return (
          <div className="space-y-4">
            {currentQuestion.context_clues && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="w-4 h-4 text-blue-400" />
                  <span className="text-blue-200 font-medium">Context Clues</span>
                </div>
                <p className="text-blue-100 text-sm">{currentQuestion.context_clues}</p>
              </div>
            )}
            <textarea
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder="Type your answer here..."
              className="w-full p-4 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/50 focus:border-blue-500/50 focus:outline-none resize-none"
              rows={3}
            />
          </div>
        );

      case 'open_ended':
      case 'scenario':
        return (
          <div className="space-y-4">
            {currentQuestion.scenario_context && (
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="w-4 h-4 text-purple-400" />
                  <span className="text-purple-200 font-medium">Scenario Context</span>
                </div>
                <p className="text-purple-100 text-sm">{currentQuestion.scenario_context}</p>
              </div>
            )}
            {currentQuestion.key_considerations && currentQuestion.key_considerations.length > 0 && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-yellow-400" />
                  <span className="text-yellow-200 font-medium">Key Considerations</span>
                </div>
                <ul className="text-yellow-100 text-sm space-y-1">
                  {currentQuestion.key_considerations.map((consideration, index) => (
                    <li key={index}>• {consideration}</li>
                  ))}
                </ul>
              </div>
            )}
            <textarea
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder="Provide a detailed response..."
              className="w-full p-4 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/50 focus:border-blue-500/50 focus:outline-none resize-none"
              rows={6}
            />
            <div className="text-xs text-white/60">
              Estimated time: {currentQuestion.estimated_time / 60} minutes
            </div>
          </div>
        );

      case 'match':
        return (
          <div className="space-y-4">
            <p className="text-white/70 text-sm">Click items from the left column, then click the matching item from the right column.</p>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <h4 className="text-white font-medium mb-3">Column A</h4>
                {currentQuestion.left_column?.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleMatchSelection('left', item)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      (userAnswer as Record<string, string>)?.[item]
                        ? 'bg-green-500/20 border-green-500/50 text-green-200'
                        : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10'
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
              <div className="space-y-2">
                <h4 className="text-white font-medium mb-3">Column B</h4>
                {currentQuestion.right_column?.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleMatchSelection('right', item)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      Object.values((userAnswer as Record<string, string>) || {}).includes(item)
                        ? 'bg-blue-500/20 border-blue-500/50 text-blue-200'
                        : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10'
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
            {Object.keys((userAnswer as Record<string, string>) || {}).length > 0 && (
              <div className="bg-white/5 rounded-lg p-4">
                <h5 className="text-white font-medium mb-2">Your Matches:</h5>
                <div className="space-y-1 text-sm">
                  {Object.entries((userAnswer as Record<string, string>) || {}).map(([left, right]) => (
                    <div key={left} className="flex items-center gap-2 text-white/80">
                      <span>{left}</span>
                      <ArrowRight className="w-4 h-4" />
                      <span>{right}</span>
                      <button
                        onClick={() => removeMatch(left)}
                        className="ml-auto text-red-400 hover:text-red-300"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const handleMatchSelection = (column: 'left' | 'right', item: string) => {
    const currentMatches = (userAnswer as Record<string, string>) || {};
    
    if (column === 'left') {
      // Remove existing match for this left item
      const newMatches = { ...currentMatches };
      delete newMatches[item];
      setUserAnswer(newMatches);
    } else {
      // Find if this right item is already matched
      const existingLeft = Object.keys(currentMatches).find(key => currentMatches[key] === item);
      if (existingLeft) {
        // Remove the existing match
        const newMatches = { ...currentMatches };
        delete newMatches[existingLeft];
        setUserAnswer(newMatches);
      }
    }
  };

  const removeMatch = (leftItem: string) => {
    const currentMatches = (userAnswer as Record<string, string>) || {};
    const newMatches = { ...currentMatches };
    delete newMatches[leftItem];
    setUserAnswer(newMatches);
  };

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Brain className="w-12 h-12 text-purple-400 animate-pulse mx-auto mb-4" />
            <p className="text-white">Loading your learning experience...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
        <div className="text-center py-12">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 mb-4">Error: {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          {phase === 'learning' ? (
            <BookOpen className="w-8 h-8 text-green-400" />
          ) : (
            <MessageCircle className="w-8 h-8 text-blue-400" />
          )}
          <div>
            <h2 className="text-2xl font-bold text-white">
              {phase === 'learning' ? 'Learning Phase' : 'Assessment Phase'}
            </h2>
            <p className="text-white/70">
              {phase === 'learning' 
                ? 'Study the material before starting the assessment' 
                : 'Interactive questions with multiple formats'
              }
            </p>
          </div>
        </div>

        {/* Phase Toggle & Stats */}
        <div className="flex items-center gap-6">
          {phase === 'learning' && (
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-white">{formatTime(studyTime)}</div>
                <div className="text-xs text-white/60">Study Time</div>
              </div>
              <button
                onClick={() => setIsStudying(!isStudying)}
                className={`p-2 rounded-lg transition-colors ${
                  isStudying ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                }`}
              >
                {isStudying ? <PauseCircle className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              </button>
            </div>
          )}
          
          {phase === 'assessment' && session && (
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-white">{session.questions_answered || 0}</div>
                <div className="text-xs text-white/60">Questions</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{Math.round(session.score || 0)}%</div>
                <div className="text-xs text-white/60">Score</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {phase === 'learning' && learningContent && (
          <motion.div
            key="learning"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Learning Content Summary */}
            <div className="bg-white/5 rounded-lg p-6 border border-white/10">
              <h3 className="text-xl font-semibold text-white mb-4">Course Overview</h3>
              <p className="text-white/80 leading-relaxed">{learningContent.summary}</p>
            </div>

            {/* Learning Objectives */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-5 h-5 text-blue-400" />
                <h4 className="text-lg font-semibold text-blue-200">Learning Objectives</h4>
              </div>
              <ul className="space-y-2">
                {learningContent.learning_objectives.map((objective, index) => (
                  <li key={index} className="flex items-start gap-2 text-blue-100">
                    <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-xs font-bold mt-0.5">
                      {index + 1}
                    </span>
                    {objective}
                  </li>
                ))}
              </ul>
            </div>

            {/* Key Concepts */}
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="w-5 h-5 text-purple-400" />
                <h4 className="text-lg font-semibold text-purple-200">Key Concepts</h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {learningContent.key_concepts.map((concept, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm"
                  >
                    {concept}
                  </span>
                ))}
              </div>
            </div>

            {/* Start Assessment Button */}
            <motion.button
              onClick={startAssessment}
              disabled={isStartingAssessment}
              className="w-full px-6 py-4 bg-gradient-to-r from-green-500 to-blue-600 text-white font-bold rounded-lg hover:from-green-600 hover:to-blue-700 transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: isStartingAssessment ? 1 : 1.02 }}
              whileTap={{ scale: isStartingAssessment ? 1 : 0.98 }}
            >
              {isStartingAssessment ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Starting Assessment...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Start Assessment
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </motion.button>
          </motion.div>
        )}

        {phase === 'assessment' && !showResult && currentQuestion && (
          <motion.div
            key="question"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Question Header */}
            <div className="flex items-center gap-4 mb-6">
              <div className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm font-medium">
                {currentQuestion.type.replace('_', ' ').toUpperCase()}
              </div>
              <div className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm">
                {currentQuestion.difficulty}
              </div>
              <div className="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm">
                {currentQuestion.topic}
              </div>
            </div>

            {/* Learning Objective */}
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-purple-400" />
                <span className="text-purple-200 font-medium">Learning Objective</span>
              </div>
              <p className="text-purple-100 text-sm">{currentQuestion.learning_objective}</p>
            </div>

            {/* Question */}
            <div className="bg-white/5 rounded-lg p-6 border border-white/10">
              <h3 className="text-xl font-semibold text-white mb-6">
                {currentQuestion.question}
              </h3>

              {renderQuestionInput()}
            </div>

            {/* Submit Button */}
            <motion.button
              onClick={submitAnswer}
              disabled={!validateAnswer() || isSubmitting}
              className="w-full px-6 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
              whileHover={{ scale: validateAnswer() && !isSubmitting ? 1.02 : 1 }}
              whileTap={{ scale: validateAnswer() && !isSubmitting ? 0.98 : 1 }}
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  Submit Answer
                </>
              )}
            </motion.button>
          </motion.div>
        )}

        {phase === 'assessment' && showResult && lastResult && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Result Header */}
            <div className={`text-center py-8 rounded-lg ${
              lastResult.correct 
                ? 'bg-green-500/20 border border-green-500/30' 
                : 'bg-red-500/20 border border-red-500/30'
            }`}>
              {lastResult.correct ? (
                <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
              ) : (
                <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
              )}
              
              <h3 className={`text-2xl font-bold mb-2 ${
                lastResult.correct ? 'text-green-200' : 'text-red-200'
              }`}>
                {lastResult.correct ? 'Correct!' : 'Incorrect'}
              </h3>
              
              <p className={`text-lg ${
                lastResult.correct ? 'text-green-100' : 'text-red-100'
              }`}>
                {lastResult.correct 
                  ? 'Great job! You got it right.' 
                  : `The correct answer was: ${JSON.stringify(lastResult.correct_answer)}`
                }
              </p>
            </div>

            {/* Explanation */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-5 h-5 text-blue-400" />
                <span className="text-blue-200 font-medium">Explanation</span>
              </div>
              <p className="text-blue-100">{lastResult.explanation}</p>
            </div>

            {/* Next Question Button */}
            {lastResult.next_question ? (
              <motion.button
                onClick={nextQuestion}
                className="w-full px-6 py-4 bg-gradient-to-r from-purple-500 to-pink-600 text-white font-bold rounded-lg hover:from-purple-600 hover:to-pink-700 transition-all flex items-center justify-center gap-3"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <ArrowRight className="w-5 h-5" />
                Next Question
              </motion.button>
            ) : (
              <motion.button
                onClick={onEndTraining}
                className="w-full px-6 py-4 bg-gradient-to-r from-green-500 to-blue-600 text-white font-bold rounded-lg hover:from-green-600 hover:to-blue-700 transition-all flex items-center justify-center gap-3"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Trophy className="w-5 h-5" />
                Complete Training
              </motion.button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};