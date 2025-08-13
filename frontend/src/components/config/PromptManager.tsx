import React, { useEffect, useState } from 'react';
import { chatService } from '../../services/chatApi';
import { RAGPromptInfo, RAGPromptCreate } from '../../types/chat';

const PromptManager: React.FC = () => {
  const [prompts, setPrompts] = useState<RAGPromptInfo[]>([]);
  const [name, setName] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await chatService.listPrompts();
      setPrompts(res.prompts);
    } catch (e: any) {
      setError(e?.message || 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const create = async (setActive: boolean) => {
    if (!name.trim() || !content.trim()) return;
    try {
      setLoading(true);
      const payload: RAGPromptCreate = { name: name.trim(), content: content.trim(), set_active: setActive };
      await chatService.createPrompt(payload);
      setName('');
      setContent('');
      await load();
    } catch (e: any) {
      setError(e?.message || 'Failed to create prompt');
    } finally {
      setLoading(false);
    }
  };

  const activate = async (id: string) => {
    await chatService.activatePrompt(id);
    await load();
  };

  const remove = async (id: string) => {
    if (!window.confirm('Delete this prompt?')) return;
    await chatService.deletePrompt(id);
    await load();
  };

  const saveEdit = async (id: string, name: string, content: string) => {
    await chatService.updatePrompt(id, { name, content });
    await load();
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">RAG Prompts</h3>

      {error && (
        <div className="mb-3 text-sm text-red-600">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 className="font-medium mb-2">Create New Prompt</h4>
          <div className="space-y-2">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Prompt name" className="w-full px-3 py-2 border rounded" />
            <textarea value={content} onChange={(e) => setContent(e.target.value)} placeholder="Prompt content" rows={8} className="w-full px-3 py-2 border rounded" />
            <div className="flex space-x-2">
              <button onClick={() => create(false)} disabled={loading} className="px-3 py-2 bg-blue-600 text-white rounded">Save</button>
              <button onClick={() => create(true)} disabled={loading} className="px-3 py-2 bg-green-600 text-white rounded">Save & Set Active</button>
            </div>
          </div>
        </div>

        <div>
          <h4 className="font-medium mb-2">Your Prompts</h4>
          {loading ? (
            <div className="text-sm text-gray-500">Loading...</div>
          ) : prompts.length === 0 ? (
            <div className="text-sm text-gray-500">No prompts yet</div>
          ) : (
            <ul className="space-y-3">
              {prompts.map(p => (
                <li key={p.prompt_id} className={`p-3 border rounded ${p.is_active ? 'border-green-400' : 'border-gray-200'}`}>
                  <div className="flex items-center justify-between">
                    <input
                      className="font-medium text-gray-800 w-1/2 mr-2 border rounded px-2 py-1"
                      defaultValue={p.name}
                      onBlur={(e) => saveEdit(p.prompt_id, e.target.value, p.content)}
                    />
                    <div className="space-x-2">
                      {!p.is_active && (
                        <button onClick={() => activate(p.prompt_id)} className="px-2 py-1 text-xs bg-green-600 text-white rounded">Activate</button>
                      )}
                      <button onClick={() => remove(p.prompt_id)} className="px-2 py-1 text-xs bg-red-600 text-white rounded">Delete</button>
                    </div>
                  </div>
                  <textarea
                    className="w-full mt-2 text-sm border rounded px-2 py-1"
                    defaultValue={p.content}
                    rows={4}
                    onBlur={(e) => saveEdit(p.prompt_id, p.name, e.target.value)}
                  />
                  {p.is_active && <div className="mt-1 text-xs text-green-700">Active</div>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default PromptManager;


