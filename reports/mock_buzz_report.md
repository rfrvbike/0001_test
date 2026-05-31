# Mock Buzz Report

Mock-only dry-run report. No X API call, token access, `.env` edit, or posting was performed.

## Genre Summary
- yokaze: 3 posts, average score 961.3
- ai_side_business: 3 posts, average score 674.0
- daily: 2 posts, average score 475.0
- unknown: 1 posts

## Genre Rankings

### yokaze
- #1 mock-mixed-yokaze-ai / buzz_score 1182 / mock_author_mixed
- #2 mock-yokaze-top / buzz_score 1162 / mock_author_1
- #3 mock-yokaze-steady / buzz_score 540 / mock_author_1

### ai_side_business
- #1 mock-ai_side_business-top / buzz_score 956 / mock_author_2
- #2 mock-mixed-ai-daily / buzz_score 695 / mock_author_mixed
- #3 mock-ai_side_business-steady / buzz_score 371 / mock_author_2

### daily
- #1 mock-daily-top / buzz_score 751 / mock_author_3
- #2 mock-daily-steady / buzz_score 199 / mock_author_3

### unknown
- #1 mock-unknown-general / buzz_score 594 / mock_author_unknown

## Genre Detection Reason Examples
- mock-ai_side_business-top: ai_side_business (matched: ai, side business, automation, paper, workflow, non-engineer)
- mock-mixed-ai-daily: ai_side_business (matched: ai, side business, automation, workflow, non-engineer, productivity)
- mock-ai_side_business-steady: ai_side_business (matched: ai, side business, automation, productivity)
- mock-daily-top: daily (matched: daily, coffee, room, sunday night, before work, habit, small joke, life)
- mock-daily-steady: daily (matched: daily, coffee, room, before work)
- mock-unknown-general: unknown (genre score 0 below min_genre_score 1)
- mock-mixed-yokaze-ai: yokaze (matched: night, relationship, lonely; tie among yokaze, ai_side_business; selected by tie_break_priority)
- mock-yokaze-top: yokaze (matched: night, hurt, relationship, lonely, healing, quiet support, woman)

## Buzz Score Top Posts
- yokaze / mock-mixed-yokaze-ai / buzz_score 1182 / rank 1 / mock_author_mixed
- yokaze / mock-yokaze-top / buzz_score 1162 / rank 2 / mock_author_1
- ai_side_business / mock-ai_side_business-top / buzz_score 956 / rank 1 / mock_author_2
- daily / mock-daily-top / buzz_score 751 / rank 1 / mock_author_3
- ai_side_business / mock-mixed-ai-daily / buzz_score 695 / rank 2 / mock_author_mixed
- unknown / mock-unknown-general / buzz_score 594 / rank 1 / mock_author_unknown
- yokaze / mock-yokaze-steady / buzz_score 540 / rank 3 / mock_author_1
- ai_side_business / mock-ai_side_business-steady / buzz_score 371 / rank 3 / mock_author_2
- daily / mock-daily-steady / buzz_score 199 / rank 2 / mock_author_3
