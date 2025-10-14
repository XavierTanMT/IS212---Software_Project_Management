# Task Manager – Firestore schema (from PlantUML) + API

## Collections (Firestore)

- **users** (`user_id`, `email`, `name`, `role`, `created_at`)
- **projects** (`name`, `key`, `owner_id`, `description`, `archived`, `created_at`)
- **memberships** (`project_id`, `user_id`, `role`, `added_at`) — doc id `{project_id}_{user_id}`
- **tasks** (`title`, `description`, `status`, `priority`, `due_date`, `created_at`, `created_by`, `assigned_to`, `project_id`, `labels`[array])
- **comments** (`task_id`, `author_id`, `body`, `created_at`, `edited_at`)
- **attachments** (`task_id`, `file_name`, `file_path`, `uploaded_by`, `upload_date`)
- **labels** (`name`, `color`)
- **task_labels** (`task_id`, `label_id`) — for filtering/indexing
- **activity** (`actor_id`, `type`, `ref_id`, `meta`, `created_at`) — audit trail
- **notifications** (`user_id`, `channel`, `title`, `body`, `read`, `created_at`)

> If you plan auth with passwords, use Firebase Auth; avoid storing `Password_Hash` in Firestore.

## Endpoints added

- **Projects**
  - `POST /api/projects` — create
  - `GET /api/projects` — list
  - `GET /api/projects/:project_id` — get
  - `PATCH /api/projects/:project_id` — update fields

- **Memberships**
  - `POST /api/memberships` — add member to project
  - `GET /api/memberships/by-project/:project_id` — list members

- **Comments**
  - `POST /api/comments` — add comment to task
  - `GET /api/comments/by-task/:task_id` — list task comments

- **Labels**
  - `POST /api/labels` — create label
  - `GET /api/labels` — list labels
  - `POST /api/labels/assign` — assign label to task
  - `POST /api/labels/unassign` — unassign label from task

- **Attachments (metadata)**
  - `POST /api/attachments` — add attachment record
  - `GET /api/attachments/by-task/:task_id` — list attachments

Existing endpoints for users, tasks, and dashboard remain unchanged.