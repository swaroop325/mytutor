/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  File,
  FileText,
  Video,
  Music,
  Image,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  Eye
} from 'lucide-react';

// File type configurations
const SUPPORTED_FILE_TYPES = {
  'application/pdf': { icon: FileText, color: 'text-red-400', category: 'document' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: FileText, color: 'text-blue-400', category: 'document' },
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': { icon: FileText, color: 'text-orange-400', category: 'document' },
  'video/mp4': { icon: Video, color: 'text-purple-400', category: 'video' },
  'video/avi': { icon: Video, color: 'text-purple-400', category: 'video' },
  'video/mov': { icon: Video, color: 'text-purple-400', category: 'video' },
  'video/quicktime': { icon: Video, color: 'text-purple-400', category: 'video' },
  'audio/mp3': { icon: Music, color: 'text-green-400', category: 'audio' },
  'audio/wav': { icon: Music, color: 'text-green-400', category: 'audio' },
  'audio/m4a': { icon: Music, color: 'text-green-400', category: 'audio' },
  'audio/mpeg': { icon: Music, color: 'text-green-400', category: 'audio' },
  'image/jpeg': { icon: Image, color: 'text-pink-400', category: 'image' },
  'image/jpg': { icon: Image, color: 'text-pink-400', category: 'image' },
  'image/png': { icon: Image, color: 'text-pink-400', category: 'image' },
  'image/gif': { icon: Image, color: 'text-pink-400', category: 'image' },
  'image/webp': { icon: Image, color: 'text-pink-400', category: 'image' }
};

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB per file
const MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024; // 2GB total

interface UploadedFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
  error?: string;
  preview?: string;
}

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  onFileRemove: (fileId: string) => void;
  disabled?: boolean;
  maxFiles?: number;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  onFileRemove,
  disabled = false,
  maxFiles = 10
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewFile, setPreviewFile] = useState<UploadedFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): { valid: boolean; error?: string } => {
    // Check file type
    if (!SUPPORTED_FILE_TYPES[file.type as keyof typeof SUPPORTED_FILE_TYPES]) {
      return {
        valid: false,
        error: `Unsupported file type: ${file.type}. Supported types: PDF, DOCX, PPTX, MP4, AVI, MOV, MP3, WAV, M4A, JPG, PNG, GIF, WebP`
      };
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return {
        valid: false,
        error: `File size exceeds ${formatFileSize(MAX_FILE_SIZE)} limit`
      };
    }

    // Check total files limit
    if (uploadedFiles.length >= maxFiles) {
      return {
        valid: false,
        error: `Maximum ${maxFiles} files allowed`
      };
    }

    // Check total size
    const totalSize = uploadedFiles.reduce((sum, f) => sum + f.file.size, 0) + file.size;
    if (totalSize > MAX_TOTAL_SIZE) {
      return {
        valid: false,
        error: `Total size exceeds ${formatFileSize(MAX_TOTAL_SIZE)} limit`
      };
    }

    return { valid: true };
  };

  const createFilePreview = async (file: File): Promise<string | undefined> => {
    if (file.type.startsWith('image/')) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.readAsDataURL(file);
      });
    }
    return undefined;
  };

  const processFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const validFiles: File[] = [];
    const newUploadedFiles: UploadedFile[] = [];

    for (const file of fileArray) {
      const validation = validateFile(file);
      
      if (validation.valid) {
        validFiles.push(file);
        const preview = await createFilePreview(file);
        
        newUploadedFiles.push({
          id: `${Date.now()}-${Math.random()}`,
          file,
          status: 'pending',
          progress: 0,
          preview
        });
      } else {
        // Show error for invalid files
        console.error(`File validation failed for ${file.name}: ${validation.error}`);
      }
    }

    if (newUploadedFiles.length > 0) {
      setUploadedFiles(prev => [...prev, ...newUploadedFiles]);
      onFilesSelected(validFiles);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFiles(files);
    }
  }, [disabled]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFiles(files);
    }
    // Reset input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
    onFileRemove(fileId);
  };

  const getFileIcon = (file: File) => {
    const config = SUPPORTED_FILE_TYPES[file.type as keyof typeof SUPPORTED_FILE_TYPES];
    const IconComponent = config?.icon || File;
    return <IconComponent className={`w-5 h-5 ${config?.color || 'text-gray-400'}`} />;
  };

  const getTotalSize = () => {
    return uploadedFiles.reduce((sum, f) => sum + f.file.size, 0);
  };

  const getSupportedFormats = () => {
    const categories = {
      document: ['PDF', 'DOCX', 'PPTX'],
      video: ['MP4', 'AVI', 'MOV'],
      audio: ['MP3', 'WAV', 'M4A'],
      image: ['JPG', 'PNG', 'GIF', 'WebP']
    };
    
    return Object.entries(categories).map(([category, formats]) => (
      <div key={category} className="text-xs text-gray-400">
        <span className="capitalize font-medium">{category}:</span> {formats.join(', ')}
      </div>
    ));
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
          ${isDragOver 
            ? 'border-blue-400 bg-blue-500/10 scale-105' 
            : 'border-white/30 bg-white/5 hover:border-white/50 hover:bg-white/10'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={Object.keys(SUPPORTED_FILE_TYPES).join(',')}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />

        <motion.div
          animate={{ scale: isDragOver ? 1.1 : 1 }}
          transition={{ duration: 0.2 }}
          className="space-y-4"
        >
          <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center ${
            isDragOver ? 'bg-blue-500/20' : 'bg-white/10'
          }`}>
            <Upload className={`w-8 h-8 ${isDragOver ? 'text-blue-400' : 'text-white/70'}`} />
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-2">
              {isDragOver ? 'Drop files here' : 'Upload Course Files'}
            </h3>
            <p className="text-white/70 mb-4">
              Drag and drop files here, or click to browse
            </p>
            
            <div className="space-y-2">
              {getSupportedFormats()}
            </div>

            <div className="mt-4 text-xs text-white/50">
              Max file size: {formatFileSize(MAX_FILE_SIZE)} • Max total: {formatFileSize(MAX_TOTAL_SIZE)} • Max files: {maxFiles}
            </div>
          </div>
        </motion.div>
      </div>

      {/* File List */}
      <AnimatePresence>
        {uploadedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-3"
          >
            <div className="flex items-center justify-between">
              <h4 className="text-lg font-semibold text-white">
                Uploaded Files ({uploadedFiles.length})
              </h4>
              <div className="text-sm text-white/70">
                Total: {formatFileSize(getTotalSize())}
              </div>
            </div>

            <div className="space-y-2">
              {uploadedFiles.map((uploadedFile) => (
                <motion.div
                  key={uploadedFile.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="bg-white/10 rounded-lg p-4 border border-white/20"
                >
                  <div className="flex items-center gap-3">
                    {/* File Icon */}
                    <div className="flex-shrink-0">
                      {getFileIcon(uploadedFile.file)}
                    </div>

                    {/* File Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h5 className="text-white font-medium truncate">
                          {uploadedFile.file.name}
                        </h5>
                        {uploadedFile.status === 'completed' && (
                          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                        )}
                        {uploadedFile.status === 'error' && (
                          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                        )}
                        {uploadedFile.status === 'uploading' && (
                          <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
                        )}
                      </div>
                      
                      <div className="flex items-center gap-4 text-sm text-white/70">
                        <span>{formatFileSize(uploadedFile.file.size)}</span>
                        <span className="capitalize">
                          {SUPPORTED_FILE_TYPES[uploadedFile.file.type as keyof typeof SUPPORTED_FILE_TYPES]?.category || 'file'}
                        </span>
                      </div>

                      {uploadedFile.error && (
                        <div className="mt-2 text-sm text-red-400">
                          {uploadedFile.error}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {uploadedFile.preview && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setPreviewFile(uploadedFile);
                          }}
                          className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                          title="Preview"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      )}
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFile(uploadedFile.id);
                        }}
                        className="p-2 text-white/70 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Remove"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {uploadedFile.status === 'uploading' && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-white/70 mb-1">
                        <span>Uploading...</span>
                        <span>{uploadedFile.progress}%</span>
                      </div>
                      <div className="w-full bg-white/20 rounded-full h-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${uploadedFile.progress}%` }}
                          className="bg-blue-500 h-2 rounded-full"
                        />
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Preview Modal */}
      <AnimatePresence>
        {previewFile && previewFile.preview && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 max-w-4xl max-h-[90vh] overflow-hidden"
            >
              <div className="flex items-center justify-between p-4 border-b border-white/20">
                <h3 className="text-lg font-semibold text-white">
                  {previewFile.file.name}
                </h3>
                <button
                  onClick={() => setPreviewFile(null)}
                  className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-4">
                <img
                  src={previewFile.preview}
                  alt={previewFile.file.name}
                  className="max-w-full max-h-[70vh] object-contain mx-auto rounded-lg"
                />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};