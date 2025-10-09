/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  Upload, 
  FileText, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Play,
  BookOpen
} from 'lucide-react';
import { FileUpload } from './FileUpload';

interface KnowledgeBaseCreatorProps {
  onKnowledgeBaseCreated: (kb: any) => void;
}

export const KnowledgeBaseCreator: React.FC<KnowledgeBaseCreatorProps> = ({
  onKnowledgeBaseCreated
}) => {
  const [step, setStep] = useState<'upload' | 'create' | 'processing'>('upload');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [knowledgeBaseName, setKnowledgeBaseName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleFilesSelected = (files: File[]) => {
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleFileRemove = (fileId: string) => {
    // Simple implementation - in real app, you'd track file IDs properly
    console.log('Remove file:', fileId);
  };

  const handleCreateKnowledgeBase = async () => {
    if (!knowledgeBaseName.trim() || selectedFiles.length === 0) {
      return;
    }

    setIsCreating(true);
    
    try {
      // First upload files to the backend
      const fileIds: string[] = [];
      
      for (const file of selectedFiles) {
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch('http://localhost:8000/api/v1/files/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });
        
        if (!uploadResponse.ok) {
          throw new Error(`Failed to upload ${file.name}`);
        }
        
        const uploadResult = await uploadResponse.json();
        fileIds.push(uploadResult.file_id);
        
        console.log(`✅ Uploaded ${file.name} with ID: ${uploadResult.file_id}`);
      }
      
      console.log(`📁 All files uploaded, creating knowledge base with IDs:`, fileIds);
      
      // Create knowledge base with actual file IDs
      const response = await fetch('http://localhost:8000/api/v1/knowledge-base/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          name: knowledgeBaseName,
          description: description,
          file_ids: fileIds
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create knowledge base');
      }

      const knowledgeBase = await response.json();
      setStep('processing');
      onKnowledgeBaseCreated(knowledgeBase);
      
    } catch (error) {
      console.error('Error creating knowledge base:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      alert(`Failed to create knowledge base: ${errorMessage}`);
    } finally {
      setIsCreating(false);
    }
  };

  const canProceed = () => {
    return knowledgeBaseName.trim().length > 0 && selectedFiles.length > 0;
  };

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
      <div className="flex items-center gap-3 mb-6">
        <Brain className="w-8 h-8 text-purple-400" />
        <h2 className="text-2xl font-bold text-white">Create Knowledge Base</h2>
      </div>

      <AnimatePresence mode="wait">
        {step === 'upload' && (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            {/* Knowledge Base Details */}
            <div className="space-y-4">
              <div>
                <label htmlFor="kbName" className="block text-white mb-2 font-medium">
                  Knowledge Base Name *
                </label>
                <input
                  type="text"
                  id="kbName"
                  value={knowledgeBaseName}
                  onChange={(e) => setKnowledgeBaseName(e.target.value)}
                  placeholder="e.g., Machine Learning Fundamentals"
                  className="w-full px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-400"
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-white mb-2 font-medium">
                  Description (Optional)
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of what this knowledge base covers..."
                  rows={3}
                  className="w-full px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-400 resize-none"
                />
              </div>
            </div>

            {/* File Upload */}
            <FileUpload
              onFilesSelected={handleFilesSelected}
              onFileRemove={handleFileRemove}
            />

            {/* Summary */}
            {selectedFiles.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4"
              >
                <h4 className="text-purple-200 font-medium mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Ready to Process
                </h4>
                <div className="text-purple-100 text-sm space-y-1">
                  <p>• {selectedFiles.length} files selected</p>
                  <p>• Knowledge Base: "{knowledgeBaseName || 'Untitled'}"</p>
                  <p>• Multi-agent processing will handle: PDF, text, audio, video, and image files</p>
                </div>
              </motion.div>
            )}

            {/* Create Button */}
            <motion.button
              onClick={handleCreateKnowledgeBase}
              disabled={!canProceed() || isCreating}
              className="w-full px-6 py-4 bg-gradient-to-r from-purple-500 to-pink-600 text-white font-bold rounded-lg hover:from-purple-600 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
              whileHover={{ scale: canProceed() && !isCreating ? 1.02 : 1 }}
              whileTap={{ scale: canProceed() && !isCreating ? 0.98 : 1 }}
            >
              {isCreating ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Creating Knowledge Base...
                </>
              ) : (
                <>
                  <Brain className="w-5 h-5" />
                  Create Knowledge Base
                </>
              )}
            </motion.button>
          </motion.div>
        )}

        {step === 'processing' && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-8"
          >
            <div className="w-20 h-20 mx-auto mb-6 bg-purple-500/20 rounded-full flex items-center justify-center">
              <Brain className="w-10 h-10 text-purple-400 animate-pulse" />
            </div>
            
            <h3 className="text-2xl font-semibold text-white mb-4">
              Knowledge Base Created!
            </h3>
            
            <p className="text-white/70 mb-6">
              Your files are being processed by our multi-agent system. You can monitor the progress and start training once processing is complete.
            </p>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
              <h4 className="text-blue-200 font-medium mb-3">What's Happening Now:</h4>
              <div className="space-y-2 text-sm text-blue-100">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>PDF Agent: Extracting text and analyzing documents</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Audio Agent: Transcribing and analyzing audio content</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Video Agent: Processing video frames and extracting content</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Text Agent: Analyzing documents and presentations</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Image Agent: Describing and analyzing visual content</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Instructions */}
      {step === 'upload' && (
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-200 mb-3">How it works:</h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm text-blue-100">
            <div>
              <h4 className="font-medium mb-2">📁 Multi-Agent Processing</h4>
              <p>Different AI agents process each file type (PDF, audio, video, text, images) simultaneously for optimal results.</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">🧠 Knowledge Base Creation</h4>
              <p>All processed content is organized into a searchable knowledge base with semantic understanding.</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">📊 Training Generation</h4>
              <p>AI generates MCQ questions, assessments, and personalized learning paths from your content.</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">🎯 Interactive Learning</h4>
              <p>Chat-based training interface adapts to your progress and provides detailed explanations.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};