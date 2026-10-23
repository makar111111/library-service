# Selected Flex tasks

The assignment permits selecting six to eight coding tasks. This project
selects the following eight, implemented in dependency order:

| Order | Branch | Assignment task | Depends on |
| --- | --- | --- | --- |
| 1 | codex/email-users-jwt | Users Service with email and JWT | Project foundation |
| 2 | codex/books-crud | Books CRUD | 1 |
| 3 | codex/book-permissions | Admin writes and public reads | 2 |
| 4 | codex/borrowing-list-detail | Borrowing model, list and detail | 1, 2 |
| 5 | codex/create-borrowing | Create borrowing and decrease inventory | 4 |
| 6 | codex/borrowing-filters | Ownership, is_active and staff user_id filters | 4, 5 |
| 7 | codex/return-borrowing | Return once and restore inventory | 5, 6 |
| 8 | codex/telegram-notifications | Notify administrators about new borrowings | 5 |

Each task has a separate branch and pull request targeting `main`. The
branches were created cumulatively and are integrated in the order above
using merge commits to preserve their shared history. The complete runnable
project is published on `main` after integration.

Submission links in implementation order:

1. [Email users and JWT](https://github.com/makar111111/library-service/pull/1)
2. [Book inventory CRUD](https://github.com/makar111111/library-service/pull/2)
3. [Book permissions](https://github.com/makar111111/library-service/pull/3)
4. [Borrowing list and details](https://github.com/makar111111/library-service/pull/4)
5. [Create borrowing](https://github.com/makar111111/library-service/pull/5)
6. [Borrowing filters](https://github.com/makar111111/library-service/pull/6)
7. [Return borrowing](https://github.com/makar111111/library-service/pull/7)
8. [Telegram notifications and final verification](https://github.com/makar111111/library-service/pull/8)

Acceptance: each task has API/behavioral tests; all tests pass; branch
coverage is at least 60%; lint, formatting, migrations and OpenAPI checks pass.

The project deliberately selects the Flex scope. Stripe payments, overdue
fines, daily overdue reports and expired payment sessions are outside these
eight tasks. Docker Compose and CI support running and verifying the project.

For the course Trello workflow, create columns To Do, In Progress, On Review
and Done; use the eight rows above as cards in the same dependency order.
Repository files do not create a Trello account or board.
