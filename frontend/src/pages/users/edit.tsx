import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useUser, useUpdateUser } from "@/hooks/use-users";

export function UserEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: user, isLoading } = useUser(Number(id));
  const updateMutation = useUpdateUser(Number(id));

  const [role, setRole] = useState("");
  const [isApiEnabled, setIsApiEnabled] = useState(false);

  useEffect(() => {
    if (user) {
      setRole(user.role);
      setIsApiEnabled(user.is_api_enabled);
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateMutation.mutateAsync({
      role: role as "admin" | "editor" | "viewer",
      is_api_enabled: isApiEnabled,
    });
    navigate("/users");
  };

  if (isLoading) {
    return <div className="p-6 text-center text-muted-foreground">Loading...</div>;
  }

  if (!user) {
    return <div className="p-6 text-center text-muted-foreground">User not found.</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" asChild>
          <Link to="/users">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">Edit User</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Edit User</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Username</Label>
              <p className="text-sm text-muted-foreground">{user.username}</p>
            </div>

            <div className="space-y-1">
              <Label>Email</Label>
              <p className="text-sm text-muted-foreground">{user.email}</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <select
                  id="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="admin">Admin</option>
                  <option value="editor">Editor</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  id="is_api_enabled"
                  checked={isApiEnabled}
                  onCheckedChange={(checked) => setIsApiEnabled(checked === true)}
                />
                <Label htmlFor="is_api_enabled">API Enabled</Label>
              </div>

              {updateMutation.isError && (
                <p className="text-sm text-destructive">
                  Failed to update user. Please try again.
                </p>
              )}

              <Button type="submit" disabled={updateMutation.isPending}>
                <Save className="h-4 w-4" />
                {updateMutation.isPending ? "Saving..." : "Save"}
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
