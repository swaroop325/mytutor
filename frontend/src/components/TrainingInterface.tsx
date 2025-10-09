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
  Lightbulb
} from 'lucide-react';

interface TrainingQuestion {
  question: string;
  options: {
    A: string;
    B: string;
    C: string;
    D: string;
  };
  correct_answer: string;
  explanation: string;
  difficulty: string;
  topic: string;
  learning_objective: string;
}

interface TrainingInterfaceProps {
  knowledgeBaseId: string;
  onEndTraining: () => void;
}

export const TrainingInterface: React.FC<TrainingInterfaceProps> = ({
  knowledgeBaseId,
  onEndTraining
}) => {
  const [session, setSession] = useState<any>(null);
  const [currentQuestion, setCurrentQuestion] = useState<TrainingQuestion | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [showResult, setShowResult] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const sessionStartedRef = useRef(false);

  useEffect(() => {
    // Prevent double calls in React StrictMode during development
    if (sessionStartedRef.current) return;
    sessionStartedRef.current = true;

    startTrainingSession();
  }, [knowledgeBaseId]);

  const startTrainingSession = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/knowledge-base/training/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          knowledge_base_id: knowledgeBaseId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start training session');
      }

      const sessionData = await response.json();
      setSession(sessionData);
      setCurrentQuestion(sessionData.current_question);
      setLoading(false);

    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!selectedAnswer || !session) return;

    setIsSubmitting(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/knowledge-base/training/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          session_id: session.id,
          answer: selectedAnswer
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit answer');
      }

      const result = await response.json();
      setLastResult(result);
      setShowResult(true);
      
      // Update session stats
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

  const nextQuestion = () => {
    if (lastResult?.next_question) {
      setCurrentQuestion(lastResult.next_question);
      setSelectedAnswer('');
      setShowResult(false);
      setLastResult(null);
    }
  };

  const endSession = async () => {
    if (!session) return;

    try {
      const response = await fetch(`http://localhost:8000/api/v1/knowledge-base/training/${session.id}/end`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        await response.json();
        // You could show final results here
        onEndTraining();
      }

    } catch (err) {
      console.error('Error ending session:', err);
      onEndTraining(); // End anyway
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'beginner':
        return 'text-green-400 bg-green-500/20';
      case 'intermediate':
        return 'text-yellow-400 bg-yellow-500/20';
      case 'advanced':
        return 'text-red-400 bg-red-500/20';
      default:
        return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Brain className="w-12 h-12 text-purple-400 animate-pulse mx-auto mb-4" />
            <p className="text-white">Starting your training session...</p>
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
            onClick={startTrainingSession}
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
          <MessageCircle className="w-8 h-8 text-blue-400" />
          <div>
            <h2 className="text-2xl font-bold text-white">Training Session</h2>
            <p className="text-white/70">Interactive Learning & Assessment</p>
          </div>
        </div>

        {/* Stats */}
        {session && (
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{session.questions_answered || 0}</div>
              <div className="text-xs text-white/60">Questions</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${getScoreColor(session.score || 0)}`}>
                {Math.round(session.score || 0)}%
              </div>
              <div className="text-xs text-white/60">Score</div>
            </div>
            <button
              onClick={endSession}
              className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors text-sm"
            >
              End Session
            </button>
          </div>
        )}
      </div>

      <AnimatePresence mode="wait">
        {!showResult && currentQuestion && (
          <motion.div
            key="question"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Question Header */}
            <div className="flex items-center gap-4 mb-6">
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getDifficultyColor(currentQuestion.difficulty)}`}>
                {currentQuestion.difficulty}
              </div>
              <div className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
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

              {/* Answer Options */}
              <div className="space-y-3">
                {Object.entries(currentQuestion.options).map(([key, value]) => (
                  <motion.button
                    key={key}
                    onClick={() => setSelectedAnswer(key)}
                    className={`w-full text-left p-4 rounded-lg border transition-all ${
                      selectedAnswer === key
                        ? 'bg-blue-500/20 border-blue-500/50 text-white'
                        : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10 hover:border-white/20'
                    }`}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-bold ${
                        selectedAnswer === key
                          ? 'border-blue-400 bg-blue-500/30 text-blue-200'
                          : 'border-white/30 text-white/60'
                      }`}>
                        {key}
                      </div>
                      <span>{value}</span>
                    </div>
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              onClick={submitAnswer}
              disabled={!selectedAnswer || isSubmitting}
              className="w-full px-6 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
              whileHover={{ scale: selectedAnswer && !isSubmitting ? 1.02 : 1 }}
              whileTap={{ scale: selectedAnswer && !isSubmitting ? 0.98 : 1 }}
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

        {showResult && lastResult && (
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
                  : `The correct answer was: ${lastResult.correct_answer}`
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

            {/* Progress Update */}
            <div className="bg-white/5 rounded-lg p-6 border border-white/10">
              <div className="flex items-center justify-between mb-4">
                <span className="text-white font-medium">Session Progress</span>
                <span className={`font-bold ${getScoreColor(lastResult.score)}`}>
                  {Math.round(lastResult.score)}%
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">{lastResult.questions_answered}</div>
                  <div className="text-white/60">Questions Answered</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">
                    {session?.correct_answers || 0}
                  </div>
                  <div className="text-white/60">Correct Answers</div>
                </div>
              </div>
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
                onClick={endSession}
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

      {/* Training Tips */}
      <div className="mt-8 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <BookOpen className="w-4 h-4 text-yellow-400" />
          <span className="text-yellow-200 font-medium">Training Tips</span>
        </div>
        <ul className="text-yellow-100 text-sm space-y-1">
          <li>• Read each question carefully and consider all options</li>
          <li>• Pay attention to the learning objectives for context</li>
          <li>• Review explanations to reinforce your understanding</li>
          <li>• Questions adapt to your performance level</li>
        </ul>
      </div>
    </div>
  );
};