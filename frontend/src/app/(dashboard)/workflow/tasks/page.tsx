'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { EmptyState } from '@/components/ui/EmptyState';
import { WorkflowStepCard } from '@/components/domain/WorkflowStepCard';
import { StepDetailDrawer, type WorkflowTask } from '@/components/workflow/StepDetailDrawer';

export default function MyTasksPage() {
  const qc = useQueryClient();
  const [selectedTask, setSelectedTask] = useState<WorkflowTask | null>(null);

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['workflow-tasks'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/workflow/instances/my-tasks/');
      return (data?.results ?? data) as WorkflowTask[];
    },
  });

  function handleReview(task: WorkflowTask) {
    setSelectedTask(task);
  }

  function handleActioned() {
    qc.invalidateQueries({ queryKey: ['workflow-tasks'] });
    setSelectedTask(null);
  }

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">My Tasks</h1>
        <p className="text-sm text-secondary mt-1">
          Pending workflow steps assigned to you
        </p>
      </div>

      <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-secondary">Loading…</div>
        ) : tasks.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="All caught up"
              description="No pending tasks assigned to you right now."
            />
          </div>
        ) : (
          <div>
            {tasks.map((task) => (
              <WorkflowStepCard
                key={task.id}
                step={{
                  id: task.id,
                  entity_id: task.entity_id,
                  borrower_name: task.borrower_name,
                  amount: task.amount,
                  loan_term_months: task.loan_term_months,
                  step_type: task.step_type,
                  submitted_at: task.submitted_at,
                  is_read: task.is_read,
                }}
                onReview={() => handleReview(task)}
              />
            ))}
          </div>
        )}
      </div>

      <StepDetailDrawer
        open={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        task={selectedTask}
        onActioned={handleActioned}
      />
    </div>
  );
}
