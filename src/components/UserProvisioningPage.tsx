import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { CheckCircle2, Loader2, Mail, RefreshCw, ShieldCheck, UserPlus } from 'lucide-react';
import { Card, CardHeader, PageHeader } from '@/components/ui/Layout';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Tabs';
import { Modal } from '@/components/ui/Modal';
import { useAuth } from '@/lib/authContext';
import { deleteManagedUser } from '@/lib/djangoApi';
import {
  getProvisioningCatalog,
  getApiFieldErrors,
  listManagedUsers,
  provisionUser,
  resendManagedUserInvite,
  setManagedUserActive,
  updateManagedUser,
  type ManagedUser,
  type ProvisioningBatch,
  type ProvisioningSubject,
  type ProvisionUserInput,
} from '@/lib/userProvisioningApi';

type FormState = {
  fullName: string;
  email: string;
  role: ProvisionUserInput['role'];
  batchId: string;
  subjectId: string;
  studentId: string;
  relationship: string;
};

const initialForm: FormState = {
  fullName: '', email: '', role: 'teacher', batchId: '', subjectId: '', studentId: '', relationship: '',
};

const statusDetails = {
  pending_setup: { label: 'Pending Setup', badge: 'pending', description: 'Waiting for the user to set their password' },
  active: { label: 'Active', badge: 'active', description: 'Can sign in' },
  disabled: { label: 'Disabled', badge: 'inactive', description: 'Account access disabled' },
} as const;

export function UserProvisioningPage() {
  const { profile } = useAuth();
  const [form, setForm] = useState<FormState>(initialForm);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [batches, setBatches] = useState<ProvisioningBatch[]>([]);
  const [subjects, setSubjects] = useState<ProvisioningSubject[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [statusTarget, setStatusTarget] = useState<string | null>(null);
  const [editing, setEditing] = useState<ManagedUser | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState('');

  const roleOptions = profile?.role === 'super_admin'
    ? [{ value: 'admin', label: 'Admin' }, { value: 'teacher', label: 'Teacher' }, { value: 'student', label: 'Student' }, { value: 'parent', label: 'Parent' }]
    : [{ value: 'teacher', label: 'Teacher' }, { value: 'student', label: 'Student' }, { value: 'parent', label: 'Parent' }];
  const selectedBatch = batches.find((batch) => batch.id === form.batchId);
  const availableSubjects = useMemo(
    () => subjects.filter((subject) => !selectedBatch || subject.course === selectedBatch.course),
    [selectedBatch, subjects],
  );
  const activeStudents = users.filter((user) => user.role === 'student' && user.isActive);

  const load = async () => {
    setError('');
    setLoading(true);
    try {
      const [managedUsers, catalog] = await Promise.all([listManagedUsers(), getProvisioningCatalog()]);
      setUsers(managedUsers);
      setBatches(catalog.batches);
      setSubjects(catalog.subjects);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'User-management data could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    const apiKey = key === 'fullName' ? 'full_name' : key === 'batchId' ? 'batch_id' : key === 'subjectId' ? 'subject_id' : key === 'studentId' ? 'student_id' : key;
    setForm((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => ({ ...current, [apiKey]: '' }));
    setError('');
    setSuccess('');
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    setError('');
    setSuccess('');
    setFieldErrors({});
    const validation: Record<string, string> = {};
    if (!form.fullName.trim()) validation.full_name = 'Full name is required.';
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) validation.email = 'Enter a valid email address.';
    if (!roleOptions.some((option) => option.value === form.role)) validation.role = 'Select a permitted role.';
    if (form.role === 'teacher' && form.subjectId && !form.batchId) validation.batch_id = 'Select a batch for this subject.';
    if (form.role === 'parent' && Boolean(form.studentId) !== Boolean(form.relationship.trim())) {
      validation.student_id = 'Select both a child and relationship, or choose Link later.';
    }
    if (Object.keys(validation).length) {
      setFieldErrors(validation);
      setError('Correct the highlighted fields and try again.');
      return;
    }
    try {
      setSubmitting(true);
      const created = await provisionUser({
        fullName: form.fullName.trim(),
        email: form.email.trim().toLowerCase(),
        role: form.role,
        batchId: form.role === 'teacher' || form.role === 'student' ? form.batchId || undefined : undefined,
        subjectId: form.role === 'teacher' ? form.subjectId || undefined : undefined,
        studentId: form.role === 'parent' ? form.studentId || undefined : undefined,
        relationship: form.role === 'parent' ? form.relationship.trim() || undefined : undefined,
      });
      setUsers(await listManagedUsers());
      setSuccess(`${created.email} was created successfully. Setup invitation generated.`);
      setForm(initialForm);
    } catch (caught) {
      setFieldErrors(getApiFieldErrors(caught));
      setError(caught instanceof Error ? caught.message : 'The user could not be created.');
    } finally {
      setSubmitting(false);
    }
  };

  const resendInvite = async (user: ManagedUser) => {
    setError('');
    setSuccess('');
    setStatusTarget(user.id);
    try {
      await resendManagedUserInvite(user.id);
      setSuccess(`A fresh setup invitation was generated for ${user.email}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The invitation could not be regenerated.');
    } finally {
      setStatusTarget(null);
    }
  };

  const toggleStatus = async (user: ManagedUser) => {
    setError('');
    setSuccess('');
    setStatusTarget(user.id);
    try {
      const updated = await setManagedUserActive(user.id, !user.isActive);
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSuccess(`${updated.email} is now ${updated.isActive ? 'active' : 'disabled'}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The account status could not be changed.');
    } finally {
      setStatusTarget(null);
    }
  };


  async function deleteUser(user: ManagedUser) {
    const confirmed = window.confirm(
      `Permanently delete ${user.fullName} (${user.email})? This action cannot be undone.`
    );

    if (!confirmed) return;

    setStatusTarget(user.id);
    setError('');
    setSuccess('');

    try {
      await deleteManagedUser(user.id);
      setUsers((current) =>
        current.filter((item) => item.id !== user.id)
      );
      setSuccess(`${user.email} was deleted successfully.`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : 'The user could not be deleted.'
      );
    } finally {
      setStatusTarget(null);
    }
  }


  const saveEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing || savingEdit) return;
    const fields = new FormData(event.currentTarget);
    setError('');
    setSuccess('');
    try {
      setSavingEdit(true);
      const updated = await updateManagedUser(editing.id, {
        fullName: String(fields.get('fullName') ?? '').trim(),
        email: String(fields.get('email') ?? '').trim().toLowerCase(),
        role: String(fields.get('role') ?? editing.role) as ManagedUser['role'],
      });
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item));
      setEditing(null);
      setSuccess(`${updated.email} was updated. Role changes require the user to sign in again.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The user could not be updated.');
    } finally {
      setSavingEdit(false);
    }
  };

  return <div>
    <PageHeader title="User Management" subtitle="Invite and manage accounts inside your institution. Role and institution authority remain server-controlled." actions={<button onClick={() => void load()} disabled={loading} className="btn-secondary"><RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} /> Refresh</button>} />
    {error && <div role="alert" className="mb-5 rounded-control border border-error-200 bg-error-50 p-3 text-sm text-error-700">{error}</div>}
    {success && <div role="status" className="mb-5 flex gap-2 rounded-control border border-success-200 bg-success-50 p-3 text-sm text-success-700"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />{success}</div>}

    <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
      <Card className="p-5 sm:p-6">
        <h2 className="font-display text-lg font-bold text-ink-950">Create and invite user</h2>
        <form onSubmit={submit} className="mt-5 space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label" htmlFor="provision-name">Full name</label><input id="provision-name" className="input" autoComplete="name" required value={form.fullName} onChange={(event) => update('fullName', event.target.value)} aria-invalid={Boolean(fieldErrors.full_name)} />{fieldErrors.full_name && <p className="mt-1 text-xs text-error-700">{fieldErrors.full_name}</p>}</div>
            <div><label className="label" htmlFor="provision-email">Email</label><input id="provision-email" className="input" type="email" autoComplete="email" required value={form.email} onChange={(event) => update('email', event.target.value)} aria-invalid={Boolean(fieldErrors.email)} />{fieldErrors.email && <p className="mt-1 text-xs text-error-700">{fieldErrors.email}</p>}</div>
          </div>
          <div><label className="label" htmlFor="provision-role">Role</label><Select id="provision-role" value={form.role} onChange={(value) => { setForm((current) => ({ ...initialForm, fullName: current.fullName, email: current.email, role: value as FormState['role'] })); setFieldErrors({}); }} options={roleOptions} />{fieldErrors.role && <p className="mt-1 text-xs text-error-700">{fieldErrors.role}</p>}<p className="mt-1.5 text-xs text-ink-500">The Django API rejects roles above your authority even if a request is tampered with.</p></div>
          {(form.role === 'teacher' || form.role === 'student') && <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label" htmlFor="provision-batch">Batch <span className="font-normal text-ink-400">(optional)</span></label><Select id="provision-batch" value={form.batchId} onChange={(value) => { update('batchId', value); update('subjectId', ''); }} options={[{ value: '', label: 'Assign later' }, ...batches.map((batch) => ({ value: batch.id, label: batch.name }))]} />{fieldErrors.batch_id && <p className="mt-1 text-xs text-error-700">{fieldErrors.batch_id}</p>}</div>
            {form.role === 'teacher' && form.batchId && <div><label className="label" htmlFor="provision-subject">Subject <span className="font-normal text-ink-400">(optional)</span></label><Select id="provision-subject" value={form.subjectId} onChange={(value) => update('subjectId', value)} options={[{ value: '', label: 'General assignment' }, ...availableSubjects.map((subject) => ({ value: subject.id, label: `${subject.code} · ${subject.title}` }))]} />{fieldErrors.subject_id && <p className="mt-1 text-xs text-error-700">{fieldErrors.subject_id}</p>}</div>}
          </div>}
          {form.role === 'parent' && <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label" htmlFor="provision-student">Linked student <span className="font-normal text-ink-400">(optional)</span></label><Select id="provision-student" value={form.studentId} onChange={(value) => update('studentId', value)} options={[{ value: '', label: 'Link later' }, ...activeStudents.map((student) => ({ value: student.id, label: student.fullName }))]} />{fieldErrors.student_id && <p className="mt-1 text-xs text-error-700">{fieldErrors.student_id}</p>}</div>
            <div><label className="label" htmlFor="provision-relationship">Relationship <span className="font-normal text-ink-400">(optional)</span></label><input id="provision-relationship" className="input" value={form.relationship} onChange={(event) => update('relationship', event.target.value)} placeholder="Required only when linking a student" />{fieldErrors.relationship && <p className="mt-1 text-xs text-error-700">{fieldErrors.relationship}</p>}</div>
          </div>}
          <button type="submit" disabled={submitting} className="btn-primary w-full justify-center sm:w-auto">{submitting ? <><Loader2 className="h-4 w-4 animate-spin" /> Sending invitation…</> : <><UserPlus className="h-4 w-4" /> Create and invite user</>}</button>
        </form>
      </Card>
      <aside className="space-y-4"><Card className="p-5"><div className="flex gap-3"><ShieldCheck className="h-5 w-5 shrink-0 text-primary-700" /><div><h2 className="font-semibold text-ink-900">Django-authoritative access</h2><p className="mt-1 text-sm leading-6 text-ink-600">Role, institution, active status, and academic relationship checks run on the server.</p></div></div></Card><Card className="p-5"><div className="flex gap-3"><Mail className="h-5 w-5 shrink-0 text-primary-700" /><div><h2 className="font-semibold text-ink-900">One-time setup</h2><p className="mt-1 text-sm leading-6 text-ink-600">Django emails a time-limited setup link. Administrators never choose or see the password.</p></div></div></Card></aside>
    </div>

    <Card className="mt-5 overflow-hidden">
      <CardHeader
        title="Managed accounts"
        subtitle="Only users inside your server-authorized scope are returned"
      />
      {loading ? (
        <div className="flex items-center gap-2 p-6 text-sm text-ink-600">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading accounts…
        </div>
      ) : users.length === 0 ? (
        <p className="p-6 text-sm text-ink-500">
          No manageable accounts were returned.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-y border-ink-200 bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-5 py-3">User</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {users.map((managedUser) => {
                const detail = statusDetails[managedUser.status];
                const busy = statusTarget === managedUser.id;

                return (
                  <tr key={managedUser.id}>
                    <td className="px-5 py-4">
                      <p className="font-medium text-ink-900">{managedUser.fullName}</p>
                      <p className="text-xs text-ink-500">{managedUser.email}</p>
                    </td>
                    <td className="px-5 py-4">
                      <Badge variant="primary">
                        <span className="capitalize">
                          {managedUser.role.replace('_', ' ')}
                        </span>
                      </Badge>
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={detail.badge} />
                      <p className="mt-1 text-xs font-medium text-ink-700">{detail.label}</p>
                      <p className="mt-0.5 text-xs text-ink-500">{detail.description}</p>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-2">
                        {managedUser.status !== 'disabled' && (
                          <button
                            type="button"
                            onClick={() => setEditing(managedUser)}
                            disabled={busy}
                            className="btn-secondary text-sm"
                          >
                            Edit
                          </button>
                        )}

                        {managedUser.status === 'pending_setup' && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void resendInvite(managedUser)}
                            className="btn-secondary text-sm"
                          >
                            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Resend Invite'}
                          </button>
                        )}

                        {managedUser.status === 'active' && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void toggleStatus(managedUser)}
                            className="btn-secondary text-sm text-error-700"
                          >
                            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Disable'}
                          </button>
                        )}

                        {managedUser.status === 'disabled' && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void toggleStatus(managedUser)}
                            className="btn-secondary text-sm"
                          >
                            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Reactivate'}
                          </button>
                        )}

                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void deleteUser(managedUser)}
                          className="btn-secondary text-sm text-error-700"
                        >
                          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Delete'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>

    <Modal
      open={Boolean(editing)}
      onClose={() => {
        if (!savingEdit) setEditing(null);
      }}
      title="Edit managed user"
      size="sm"
    >
      {editing && (
        <form onSubmit={saveEdit} className="space-y-4">
          <div>
            <label className="label" htmlFor="edit-user-name">Full name</label>
            <input
              id="edit-user-name"
              name="fullName"
              className="input"
              required
              defaultValue={editing.fullName}
              disabled={savingEdit}
            />
          </div>
          <div>
            <label className="label" htmlFor="edit-user-email">Email</label>
            <input
              id="edit-user-email"
              name="email"
              type="email"
              className="input"
              required
              defaultValue={editing.email}
              disabled={savingEdit}
            />
          </div>
          <div>
            <label className="label" htmlFor="edit-user-role">Role</label>
            <select
              id="edit-user-role"
              name="role"
              className="input"
              defaultValue={editing.role}
              disabled={savingEdit}
            >
              {roleOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs leading-5 text-ink-500">
            Institution and account status cannot be changed through this form.
            The backend validates every role change.
          </p>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setEditing(null)}
              disabled={savingEdit}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button type="submit" disabled={savingEdit} className="btn-primary">
              {savingEdit ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Saving…
                </>
              ) : (
                'Save changes'
              )}
            </button>
          </div>
        </form>
      )}
    </Modal>
  </div>;
}
