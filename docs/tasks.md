# Selected Flex tasks

The assignment permits selecting six to eight coding tasks. This project
selects the following eight, implemented in dependency order:

| Order | Branch | Assignment task | Depends on |
| --- | --- | --- | --- |
| 1 | feature/email-users-jwt | Users Service with email and JWT | Project foundation |
| 2 | feature/books-crud | Books CRUD | 1 |
| 3 | feature/book-permissions | Admin writes and public reads | 2 |
| 4 | feature/borrowing-list-detail | Borrowing model, list and detail | 1, 2 |
| 5 | feature/create-borrowing | Create borrowing and decrease inventory | 4 |
| 6 | feature/borrowing-filters | Ownership, is_active and staff user_id filters | 4, 5 |
| 7 | feature/return-borrowing | Return once and restore inventory | 5, 6 |
| 8 | feature/telegram-notifications | Notify administrators about new borrowings | 5 |

Each task has a separate branch and pull request to `main`. Branches are
cumulative because merging requires review. Review and merge in the order
above using merge commits, preserving commit ancestry. Later PR diffs shrink
as earlier PRs merge. No automatic merging is performed.

Acceptance: each task has API/behavioral tests; all tests pass; branch
coverage is at least 60%; lint, formatting, migrations and OpenAPI checks pass.

The project deliberately selects the Flex scope. Stripe payments, overdue
fines, daily overdue reports and expired payment sessions are outside these
eight tasks. Docker Compose and CI support running and verifying the project.

For the course Trello workflow, create columns To Do, In Progress, On Review
and Done; use the eight rows above as cards in the same dependency order.
Repository files do not create a Trello account or board.
