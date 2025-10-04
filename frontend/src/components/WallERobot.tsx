import { motion } from 'framer-motion';

interface WallERobotProps {
  className?: string;
}

export const WallERobot = ({ className = '' }: WallERobotProps) => {
  return (
    <motion.div
      className={`relative ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
    >
      {/* Robot Body */}
      <motion.div
        className="relative w-48 h-56"
        animate={{
          y: [0, -10, 0],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        {/* Head/Eyes Container */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-20 bg-gradient-to-b from-gray-700 to-gray-800 rounded-t-3xl border-4 border-gray-600">
          {/* Eyes */}
          <div className="flex justify-around items-center h-full px-4">
            <motion.div
              className="w-8 h-8 bg-blue-400 rounded-full relative overflow-hidden"
              animate={{
                scaleY: [1, 0.1, 1],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                repeatDelay: 2,
              }}
            >
              <div className="absolute inset-0 bg-gradient-radial from-white to-transparent opacity-50" />
              <div className="absolute top-1 left-1 w-3 h-3 bg-white rounded-full" />
            </motion.div>
            <motion.div
              className="w-8 h-8 bg-blue-400 rounded-full relative overflow-hidden"
              animate={{
                scaleY: [1, 0.1, 1],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                repeatDelay: 2,
              }}
            >
              <div className="absolute inset-0 bg-gradient-radial from-white to-transparent opacity-50" />
              <div className="absolute top-1 left-1 w-3 h-3 bg-white rounded-full" />
            </motion.div>
          </div>
        </div>

        {/* Neck */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-12 h-8 bg-gray-700 border-4 border-gray-600" />

        {/* Main Body */}
        <div className="absolute top-28 left-1/2 -translate-x-1/2 w-36 h-28 bg-gradient-to-b from-yellow-600 to-yellow-700 rounded-lg border-4 border-yellow-800">
          {/* Logo/Badge Area */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 w-20 h-16 bg-yellow-800 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">myTutor</span>
          </div>

          {/* Track wheels indicator */}
          <div className="absolute -bottom-2 left-2 right-2 h-4 bg-gray-800 rounded-full" />
        </div>

        {/* Arms */}
        <motion.div
          className="absolute top-32 -left-6 w-12 h-6 bg-gray-700 rounded-full border-2 border-gray-600"
          animate={{
            rotate: [0, -10, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute top-32 -right-6 w-12 h-6 bg-gray-700 rounded-full border-2 border-gray-600"
          animate={{
            rotate: [0, 10, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>
    </motion.div>
  );
};
