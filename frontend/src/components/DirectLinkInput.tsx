/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, Plus, X, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react';

interface DirectLink {
  id: string;
  url: string;
  status: 'pending' | 'validating' | 'valid' | 'invalid';
  error?: string;
  title?: string;
  type?: string;
}

interface DirectLinkInputProps {
  onLinksChange: (links: string[]) => void;
  disabled?: boolean;
  maxLinks?: number;
}

export const DirectLinkInput: React.FC<DirectLinkInputProps> = ({
  onLinksChange,
  disabled = false,
  maxLinks = 20
}) => {
  const [links, setLinks] = useState<DirectLink[]>([]);
  const [newLinkUrl, setNewLinkUrl] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const validateUrl = (url: string): boolean => {
    try {
      const urlObj = new URL(url);
      return ['http:', 'https:'].includes(urlObj.protocol);
    } catch {
      return false;
    }
  };

  const detectLinkType = (url: string): string => {
    const urlLower = url.toLowerCase();
    
    if (urlLower.includes('youtube.com') || urlLower.includes('youtu.be')) {
      return 'YouTube Video';
    }
    if (urlLower.includes('vimeo.com')) {
      return 'Vimeo Video';
    }
    if (urlLower.includes('.pdf')) {
      return 'PDF Document';
    }
    if (urlLower.includes('.mp4') || urlLower.includes('.avi') || urlLower.includes('.mov')) {
      return 'Video File';
    }
    if (urlLower.includes('.mp3') || urlLower.includes('.wav') || urlLower.includes('.m4a')) {
      return 'Audio File';
    }
    if (urlLower.includes('.docx') || urlLower.includes('.doc')) {
      return 'Word Document';
    }
    if (urlLower.includes('.pptx') || urlLower.includes('.ppt')) {
      return 'PowerPoint';
    }
    if (urlLower.includes('.jpg') || urlLower.includes('.png') || urlLower.includes('.gif')) {
      return 'Image';
    }
    
    return 'Web Resource';
  };

  const addLink = async () => {
    if (!newLinkUrl.trim() || links.length >= maxLinks) return;

    const url = newLinkUrl.trim();
    
    if (!validateUrl(url)) {
      return;
    }

    // Check for duplicates
    if (links.some(link => link.url === url)) {
      return;
    }

    const newLink: DirectLink = {
      id: `${Date.now()}-${Math.random()}`,
      url,
      status: 'validating',
      type: detectLinkType(url)
    };

    setLinks(prev => [...prev, newLink]);
    setNewLinkUrl('');
    setIsValidating(true);

    // Simulate validation (in real implementation, this would be an API call)
    setTimeout(() => {
      setLinks(prev => prev.map(link => 
        link.id === newLink.id 
          ? { ...link, status: 'valid', title: `Resource from ${new URL(url).hostname}` }
          : link
      ));
      setIsValidating(false);
      
      // Update parent component
      const validUrls = [...links.filter(l => l.status === 'valid').map(l => l.url), url];
      onLinksChange(validUrls);
    }, 1000);
  };

  const removeLink = (linkId: string) => {
    setLinks(prev => prev.filter(link => link.id !== linkId));
    
    // Update parent component
    const remainingUrls = links.filter(link => link.id !== linkId && link.status === 'valid').map(link => link.url);
    onLinksChange(remainingUrls);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addLink();
    }
  };

  const getStatusIcon = (status: DirectLink['status']) => {
    switch (status) {
      case 'validating':
        return <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />;
      case 'valid':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'invalid':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      {/* Input Section */}
      <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
        <div className="flex items-center gap-3 mb-4">
          <Link className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Direct Resource Links</h3>
        </div>
        
        <div className="flex gap-3">
          <input
            type="url"
            value={newLinkUrl}
            onChange={(e) => setNewLinkUrl(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="https://example.com/resource.pdf"
            className="flex-1 px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-400"
            disabled={disabled || links.length >= maxLinks}
          />
          <motion.button
            onClick={addLink}
            disabled={!newLinkUrl.trim() || disabled || links.length >= maxLinks || isValidating}
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Plus className="w-4 h-4" />
            Add Link
          </motion.button>
        </div>

        <div className="mt-3 text-sm text-white/70">
          Supported: YouTube videos, PDFs, documents, images, audio/video files, and web resources
        </div>
        
        {links.length > 0 && (
          <div className="mt-2 text-xs text-white/50">
            {links.length} of {maxLinks} links added
          </div>
        )}
      </div>

      {/* Links List */}
      <AnimatePresence>
        {links.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-2"
          >
            {links.map((link) => (
              <motion.div
                key={link.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="bg-white/10 rounded-lg p-4 border border-white/20"
              >
                <div className="flex items-center gap-3">
                  {/* Status Icon */}
                  <div className="flex-shrink-0">
                    {getStatusIcon(link.status)}
                  </div>

                  {/* Link Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h5 className="text-white font-medium truncate">
                        {link.title || new URL(link.url).hostname}
                      </h5>
                      {link.type && (
                        <span className="px-2 py-1 bg-blue-500/20 text-blue-300 text-xs rounded-full">
                          {link.type}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-sm text-white/70">
                      <span className="truncate">{link.url}</span>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 flex-shrink-0"
                        title="Open in new tab"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    {link.error && (
                      <div className="mt-2 text-sm text-red-400">
                        {link.error}
                      </div>
                    )}
                  </div>

                  {/* Remove Button */}
                  <button
                    onClick={() => removeLink(link.id)}
                    className="p-2 text-white/70 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors flex-shrink-0"
                    title="Remove link"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Instructions */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <h4 className="text-blue-200 font-medium mb-2">Supported Link Types:</h4>
        <ul className="text-sm text-blue-100 space-y-1">
          <li>• YouTube and Vimeo videos</li>
          <li>• PDF documents and presentations</li>
          <li>• Word documents and PowerPoint files</li>
          <li>• Audio files (MP3, WAV, M4A)</li>
          <li>• Video files (MP4, AVI, MOV)</li>
          <li>• Images and other web resources</li>
        </ul>
      </div>
    </div>
  );
};