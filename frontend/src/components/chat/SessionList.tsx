/**
 * Session list component for managing chat sessions
 */

import React from 'react';
import { MessageSquare, Trash2, Plus, Calendar } from 'lucide-react';
import { ConversationInfo } from '../../types/chat';

interface SessionListProps {
  sessions: ConversationInfo[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onNewSession: () => void;
}

const SessionList: React.FC<SessionListProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  onNewSession,
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) {
      return 'Today';
    } else if (diffDays === 2) {
      return 'Yesterday';
    } else if (diffDays <= 7) {
      return `${diffDays - 1} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const truncateTitle = (title: string, maxLength: number = 40) => {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  };

  // Group sessions by date
  const groupedSessions = sessions.reduce((groups, session) => {
    const date = formatDate(session.last_activity);
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(session);
    return groups;
  }, {} as Record<string, ConversationInfo[]>);

  // Sort groups by recency
  const sortedGroups = Object.entries(groupedSessions).sort(([a], [b]) => {
    const order = ['Today', 'Yesterday'];
    const aIndex = order.indexOf(a);
    const bIndex = order.indexOf(b);
    
    if (aIndex !== -1 && bIndex !== -1) {
      return aIndex - bIndex;
    } else if (aIndex !== -1) {
      return -1;
    } else if (bIndex !== -1) {
      return 1;
    } else {
      return b.localeCompare(a);
    }
  });

  return (
    <div className="flex-1 flex flex-col">
      {/* New session button */}
      <div className="p-4 border-b">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-6 text-center">
            <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No chat sessions yet</p>
            <p className="text-gray-400 text-xs mt-1">Start a new conversation to begin</p>
          </div>
        ) : (
          <div className="space-y-6 p-4">
            {sortedGroups.map(([dateGroup, groupSessions]) => (
              <div key={dateGroup}>
                <div className="flex items-center mb-3">
                  <Calendar className="w-4 h-4 text-gray-400 mr-2" />
                  <h3 className="text-sm font-medium text-gray-600">{dateGroup}</h3>
                </div>
                
                <div className="space-y-2">
                  {groupSessions
                    .sort((a, b) => new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime())
                    .map((session) => (
                      <div
                        key={session.conversation_id}
                        className={`group relative p-3 rounded-lg cursor-pointer transition-all ${
                          currentSessionId === session.conversation_id
                            ? 'bg-blue-50 border-2 border-blue-200'
                            : 'bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                        }`}
                        onClick={() => onSelectSession(session.conversation_id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center mb-1">
                              <MessageSquare className="w-4 h-4 text-gray-400 mr-2 flex-shrink-0" />
                              <h4 className="text-sm font-medium text-gray-800 truncate">
                                {truncateTitle(session.title)}
                              </h4>
                            </div>
                            
                            <div className="flex items-center justify-between text-xs text-gray-500">
                              <span>{session.message_count} messages</span>
                              <span>
                                {new Date(session.last_activity).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </span>
                            </div>
                          </div>

                          {/* Delete button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm('Are you sure you want to delete this chat session?')) {
                                onDeleteSession(session.conversation_id);
                              }
                            }}
                            className="opacity-0 group-hover:opacity-100 ml-2 p-1 text-gray-400 hover:text-red-500 transition-all"
                            title="Delete session"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>

                        {/* Active indicator */}
                        {currentSessionId === session.conversation_id && (
                          <div className="absolute left-0 top-3 bottom-3 w-1 bg-blue-500 rounded-r"></div>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionList;