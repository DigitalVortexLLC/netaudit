import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Pencil, Trash2, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuditComments, useCreateComment, useUpdateComment, useDeleteComment } from "@/hooks/use-comments";
import { useAuth } from "@/hooks/use-auth";

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface CommentSectionProps {
  auditId: number;
}

export function CommentSection({ auditId }: CommentSectionProps) {
  const { user } = useAuth();
  const { data: comments = [] } = useAuditComments(auditId);
  const createComment = useCreateComment(auditId);
  const updateComment = useUpdateComment(auditId);
  const deleteComment = useDeleteComment(auditId);

  const [newContent, setNewContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  const handleSubmit = async () => {
    if (!newContent.trim()) return;
    await createComment.mutateAsync(newContent);
    setNewContent("");
  };

  const handleUpdate = async (commentId: number) => {
    if (!editContent.trim()) return;
    await updateComment.mutateAsync({ commentId, content: editContent });
    setEditingId(null);
    setEditContent("");
  };

  const startEdit = (commentId: number, content: string) => {
    setEditingId(commentId);
    setEditContent(content);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Comments ({comments.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Comment list */}
        {comments.map((comment) => (
          <div key={comment.id} className="border border-border rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-semibold">{comment.author_name}</span>
                <span className="text-muted-foreground">{timeAgo(comment.created_at)}</span>
                {comment.created_at !== comment.updated_at && (
                  <span className="text-muted-foreground text-xs">(edited)</span>
                )}
              </div>
              {user && comment.author === user.id && (
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => startEdit(comment.id, comment.content)}
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={() => deleteComment.mutate(comment.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
            {editingId === comment.id ? (
              <div className="space-y-2">
                <Textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={3}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleUpdate(comment.id)} disabled={updateComment.isPending}>
                    Save
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="prose prose-sm prose-invert max-w-none">
                <ReactMarkdown>{comment.content}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}

        {/* New comment form */}
        <div className="border-t border-border pt-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">New comment</span>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => setShowPreview(!showPreview)}
            >
              {showPreview ? "Edit" : "Preview"}
            </Button>
          </div>
          {showPreview ? (
            <div className="prose prose-sm prose-invert max-w-none border border-border rounded-md p-3 min-h-[80px]">
              <ReactMarkdown>{newContent || "*Nothing to preview*"}</ReactMarkdown>
            </div>
          ) : (
            <Textarea
              placeholder="Write a comment... (supports markdown)"
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              rows={3}
            />
          )}
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={!newContent.trim() || createComment.isPending}
          >
            {createComment.isPending ? "Posting..." : "Post comment"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
