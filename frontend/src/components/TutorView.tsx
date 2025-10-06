import { GraduationCap } from 'lucide-react';

export const TutorView = () => {
  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
        <GraduationCap className="text-blue-400" />
        AI Tutor
      </h2>
      <p className="text-gray-300">
        AI Tutor feature coming soon. You'll be able to select courses and test your knowledge with AI-generated questions.
      </p>
    </div>
  );
};
