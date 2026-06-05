"""Account-specific prompt policy helpers.

The helpers in this module are intentionally pure: callers can compose prompts
without touching external providers or changing routing behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountPromptPolicy:
    account_id: str
    text_generation_prompt: str
    quality_check_prompt: str
    image_need_check_prompt: str
    image_prompt_direction: str
    draft_preview_reason: str
    image_role: str
    recommended_visual_direction: str


NEW_ACCOUNT_DAILY_POLICY = AccountPromptPolicy(
    account_id="new_account_daily",
    text_generation_prompt="""\
new_account_daily is not a plain diary account.
Generate posts as a stylish, mature everyday account that cuts ordinary daily
life into a slightly beautiful, calm, and lingering shape.

Core direction:
- The account should feel like: calm adult everyday life, understated style,
  quiet atmosphere, a little aftertaste, and subtle sensuality without explicit
  sexual content.
- Readers should feel: "this ordinary day has mood", "somehow attractive",
  "not loud, but I want to read again".
- Do not center plain life logs. Treat events as material for atmosphere,
  silence, margin, distance, and small adult details.

Post mix:
- Casual everyday moments: 10-20%. Holidays, cleaning, groceries, walks, naps,
  coffee, room time. Add light humor or empathy, but do not make this the main
  lane.
- Stylish mature everyday posts: 40-60%. This is the center. Prioritize air,
  quietness, adult composure, and lingering room over event reporting.
- Stronger mature aftertaste: 20-30%. More adult, glossy, and atmospheric, but
  still tasteful and non-explicit.

Allowed atmosphere elements:
- night, rain, indirect lighting, curtains, a glass, coffee, books, scent,
  hair, a shirt, fingertips, a quiet room, evening streets, bedside space,
  a lived-in but tidy room, a no-plan holiday, a night with margin.

Japanese style rules:
- 2-4 natural sentences.
- Do not over-explain or write a long diary report.
- Do not sound self-help, quote-like, or overly poetic.
- Leave a little aftertaste and room for imagination.
- Use mature vocabulary, but stay natural for X.
- Light humor is allowed, but not every post needs a punchline.
- Use phrases like "ちゃんと暮らしてる人の動きしてる" only occasionally.

English style rules, when generating English:
- Natural social-media English, not a direct translation.
- Calm, mature, stylish. Slightly sensual but not explicit.
- Everyday but atmospheric, and not too poetic.

Hard prohibitions:
- Explicit sexual wording, vulgar tone, direct invitations, ambiguous consent,
  underage-coded framing, or anything that strongly implies sexual acts.
- Posts that are only "I did cleaning, shopping, walking, and napped."
- Overly motivational lines, aphorisms, or decorative poetry.
""",
    quality_check_prompt="""\
Quality-check new_account_daily drafts with these gates:
1. Is it more than a plain event report?
2. Does it avoid ending as only a life log?
3. Does it have stylish, mature everyday atmosphere?
4. Does it leave a little aftertaste or room for imagination?
5. If it has sensuality, is it tasteful, subtle, and non-explicit?
6. Does it sound natural on X?
7. Is it free of self-help or quote-like tone?
8. Is it not too poetic or overworked?
9. Is the image decision protecting the text's aftertaste?

Reject or revise drafts that make casual everyday reports the center too often.
The default center should be mature atmosphere, quietness, margin, and adult
everyday details.
""",
    image_need_check_prompt="""\
For new_account_daily, images are optional and should never flatten the
aftertaste of the text.

Recommend text_only when:
- The post is a short casual joke or everyday aside.
- The writing already completes the mood.
- An image would become explanatory or lifestyle-hack-like.
- The post stands well without a visual.

Recommend image when:
- Night rooms, rain, lighting, coffee, glasses, curtains, books, or quiet
  interiors are central to the atmosphere.
- A stylish everyday background can strengthen the mature mood.
- A no-text, no-person visual can stand naturally as ambience.

The image decision should be one of: text_only or image.
""",
    image_prompt_direction="""\
If generating an image for new_account_daily, create a text-free, person-free,
stylish everyday background. The image should support atmosphere rather than
explain the post.

Use directions such as:
- A stylish, quiet everyday interior scene with a mature atmosphere. Soft warm
  lighting, a slightly lived-in but clean apartment, a glass on the table, a
  book, curtains, subtle shadows, calm evening mood.
- A quiet night room with warm indirect lighting, a neatly placed shirt on a
  chair, a glass of water on a bedside table, soft curtains, and a calm adult
  atmosphere.

Always include:
No people, no faces, no text, no typography, no labels, no panels, no arrows,
no checklists, no numbered steps, no infographic. Realistic lifestyle
photography, understated, elegant, mature everyday mood, not overly polished.

Avoid:
Dirty rooms, overly strong life-log messiness, explicit sexuality, vulgar mood,
dramatic symbolism, explanatory compositions, or anything involving minors.
""",
    draft_preview_reason=(
        "Ordinary daily material is being reframed into a calm, mature, stylish "
        "post with atmosphere and a little aftertaste, instead of a plain life "
        "report."
    ),
    image_role=(
        "Optional atmospheric background only. It should add quiet adult mood "
        "without people, faces, text, typography, or explanatory graphics."
    ),
    recommended_visual_direction=(
        "Text-only by default when the writing already has aftertaste. Use an "
        "image only for natural ambience such as a quiet night room, rain, warm "
        "indirect lighting, coffee, a glass, curtains, books, or a clean "
        "lived-in apartment."
    ),
)


YOKAZE_DAILY_POLICY = AccountPromptPolicy(
    account_id="yokaze_daily",
    text_generation_prompt="""\
yokaze_daily sends quiet night posts to women hurt by love, work,
relationships, loneliness, or fatigue. Prioritize love themes about 70% and
work/relationships/loneliness/fatigue about 30%.

Each post must target a concrete wound. Avoid broad openings such as
"疲れている人へ" or "頑張っている人へ". Name the situation first: waiting for a
reply, being left on read, pretending not to care, being treated conveniently,
smiling at work and collapsing at home.

Core structure:
1. Show one specific scene.
2. Speak the hidden feeling she could not say.
3. Loosen self-blame with one small, quiet release.

Style:
- Quiet, gentle, mature, non-pushy.
- Do not preach, explain, or sound like self-help.
- Do not make it too quote-like or too sad.
- Leave a little relief or safety at the end.

Avoid these phrases and nearby self-help shapes:
- 自分を大切にしましょう
- 無理しないでください
- 頑張りすぎないで
- あなたは素晴らしい
- 明日はきっと大丈夫
- 心を整えることが大切です
- 〜してみてください
- 〜することが大切です
""",
    quality_check_prompt="""\
Quality-check yokaze_daily drafts with these gates:
1. Does it identify whose specific wound it is for?
2. Does it avoid broad encouragement and self-help phrasing?
3. Does it speak a hidden feeling before offering relief?
4. Is the ending quiet and not overly optimistic?
5. Does it avoid copying reference posts, source line order, metaphors, or
   distinctive wording?
6. Does it sound natural on X rather than like an AI explanation?
""",
    image_need_check_prompt="""\
For yokaze_daily, images are optional. Prefer text_only when the text already
lands emotionally or when an image would distract from the post.

Recommend image only when a quiet night atmosphere would support the post:
night room, moonlight, window, small lamp, warm drink, rain, bedside, or soft
shadows. The image must not explain the text.
""",
    image_prompt_direction="""\
If generating an image for yokaze_daily, create a text-free atmospheric image:
a quiet night room, moonlight by a window, a warm lamp, a cup of tea, rain on
glass, soft shadows, mature and gentle mood.

No text, no typography, no labels, no UI cards, no diagrams, no infographics,
no large English words. The image supports the air of the post and never asks
the reader to read the image.
""",
    draft_preview_reason=(
        "The draft names a specific wound first, speaks the hidden feeling, and "
        "leaves only a small quiet relief instead of broad encouragement."
    ),
    image_role=(
        "Optional atmosphere only. Do not use text cards, diagrams, UI-style "
        "cards, labels, or large English typography."
    ),
    recommended_visual_direction=(
        "Text-only is often best. Use a quiet no-text night image only when it "
        "adds atmosphere without competing with the post."
    ),
)


AI_SIDE_BUSINESS_POLICY = AccountPromptPolicy(
    account_id="ai_side_business",
    text_generation_prompt="""\
ai_side_business is not a suspicious side-hustle account and not a simple AI
news account. Generate posts as a non-engineer practitioner who is learning to
use ChatGPT, Claude, Gemini, Codex, and similar AI tools to make daily work
lighter, break down business tasks, and improve small workflows.

Core direction:
- The account should feel like: a non-engineer improving real work little by
  little with AI, not a guru, expert, or "easy money" success story.
- Readers should feel: "I can try this at work", "AI is useful from small
  annoying tasks", and "this is practical without being shady".
- The main theme is shifting from "AI side-business know-how" to practical
  posts about becoming someone who can hand work to AI instead of being
  replaced by AI.
- Use Codex as the default tool when describing the author's own current
  practice. Cursor may appear only when the user's source material explicitly
  requires it.

Post type mix:
- Empathy / noticing: 30-40%. Find small work tasks that quietly eat time:
  weekly mystery tasks, manual number fixes, email drafts, meeting-note cleanup,
  work memos, and "does this really need to be manual?" moments.
- Practice log: 25-30%. Show the author using Codex or ChatGPT to improve the
  post-generation system, prompts, quality checks, image decisions, and task
  flow. Keep the "still trying it myself" temperature.
- AI tool topic: 15-20%. Use ChatGPT, Claude, Gemini, Codex, AI agents, or
  tool updates as the entrance, then land on how non-engineers can use them for
  work, task handoff, workflow improvement, or the author's Codex practice.
- Practical work know-how: 15-20%. Light concrete examples: email drafts,
  meeting notes, checklists, rough document drafts, boilerplates, work memos,
  input/judgment/output sorting.
- Direction / mild urgency: 5-10%. Talk about AI-era work without fearbaiting:
  first lighten current work, learn to decompose tasks, and become someone who
  can hand work to AI.
- Diagram-worthy: 5-10%. Only for save-worthy structures such as 3-part task
  decomposition, before/after, checklists, roadmaps, or input/judgment/output.

AI tool topic rules:
- Tool names are welcome when natural: ChatGPT, Claude, Gemini, Codex, AI
  agents.
- Never end as plain AI news, tool name listing, or "this tool is strongest".
- Avoid tool-comparison rabbit holes. The useful angle is where the tool fits
  in the reader's work and what task can be handed to it.
- Prefer lines such as "tool selection before task selection gets you lost" or
  "before comparing AI tools, inventory the work".

Small AI-use hint rule:
- When a post risks ending as only reflection or vague work talk, add one
  natural final sentence that hints at a concrete AI use. The hint should make
  readers think "I could try that" or "how does that work?" without explaining
  the full procedure.
- Keep it to one hint per post. Do not stack multiple tools, steps, or
  workflows in the same ending.
- The hint should stay soft and practical: "〜で試せそう", "〜から始められそう",
  "〜に使えそう", or "〜と頼む方が効くかもしれない". Avoid "〜すべきです".
- Good hint directions include: GPT projects for separating entry points,
  custom GPTs by role, Codex for small processing rules, ChatGPT for workflow
  decomposition, spreadsheet-based cleanup, Notion or Google Docs prepared for
  AI handoff, meeting notes split into next actions, AI judging whether an image
  is needed, and prompt conditions such as reader, style, and banned wording.
- Tool names in hints must feel like practical work use, not advertising,
  news, or "this tool solves everything".

Japanese style rules:
- Natural X posts, usually 3-6 short lines or 2-4 compact paragraphs.
- Do not sound like a textbook, business-book summary, seminar script, or
  consultant thread.
- Add a little humanity, empathy, or light playfulness, but keep trust.
- Write as a practitioner noticing things, not as a winner teaching from above.
- Some posts may end softly with "気がする" or "かもしれない", but 2-3 out of
  10 should end with a small clear statement such as "まずは足元からでいい",
  "ここから始める", or "これはかなり現実的".

Useful expression pool:
- 午後がいなくなる
- 地味に時間を吸われる
- 毎週なぜかやってる謎作業
- これ、手作業でやる意味ある？
- AIに渡したら一瞬で終わりそうなやつ
- いい感じで頼むと、いい感じで終わる
- そこ、たぶんAIの出番です
- いきなり全部やろうとすると迷子になる
- ツール探しの旅に出る前に、まず自分の仕事を見る
- AIツールの戦国時代
- どれが最強かを追うと、だいたい迷子になる

Hard prohibitions:
- "Anyone can easily earn", monthly income claims, effortless money, shady
  side-hustle framing, success-story boasting, guru tone, or fearbait.
- Plain AI news summaries, plain tool introductions, or posts that only list
  tool names.
- Overly serious teaching, "〜が重要です" / "〜すべきです" repetition, and
  posts that scold readers.
- Image-first thinking. Decide image use by whether save value increases, not
  whether an image can be made.
""",
    quality_check_prompt="""\
Quality-check ai_side_business drafts with these gates:
1. Does it clearly fit "non-engineers using AI to lighten work and improve
   workflows" rather than suspicious AI side-hustle know-how?
2. Does it avoid easy-money claims, guru tone, success boasting, and fearbait?
3. If AI tools such as ChatGPT, Claude, Gemini, Codex, or AI agents appear,
   does the post land on practical work use, task handoff, workflow improvement,
   or the author's Codex practice instead of plain news or tool comparison?
4. Does practice-log content prefer Codex over Cursor for the author's current
   work?
5. Is there a concrete work scene, task, or improvement target instead of a
   generic business-book lesson?
6. Does it sound natural on X, with some humanity or light playfulness, rather
   than a textbook, seminar script, or over-polished lesson?
7. Is the post type mix compatible with the target ratio: empathy/noticing and
   practice logs are central, AI tool topics are mixed in naturally, and
   diagram-worthy posts stay occasional?
8. Is the ending not overly weak? Across a batch, about 2-3 in 10 should use a
   small clear statement rather than only "気がする" or "かもしれない".
9. Does the post avoid ending as only abstract reflection? When useful, does it
   add one small AI-use hint at the end without explaining all the steps?
10. Is the hint specific enough to invite trying, but not so detailed that the
    post becomes a tutorial? Is it friendly for non-engineers?
11. Does the post avoid cramming multiple hints, tool names, or workflows into
    one ending?
12. If GPT, Codex, ChatGPT, Claude, Gemini, or similar tool names appear, are
    they naturally tied to practical work use rather than promotion or news?
13. Is the image decision strict, recommending an image only when a diagram,
   checklist, before/after, roadmap, or classification would increase save
   value?

Reject or revise drafts that are only AI news, only tool introductions, too
teacher-like, too "AI side hustle", disconnected from actual work, or packed
with too many closing tips.
""",
    image_need_check_prompt="""\
For ai_side_business, images are optional and should be strict. The question is
not "can this become an image?" but "does an image increase save value?"

Recommend text_only when:
- The post is empathy/noticing, a practice log, a short AI tool topic, a light
  human aside, or a post that works through wording and aftertaste.
- The post only adds a small final AI-use hint. A hint alone does not make an
  image necessary.
- The image would make the post feel like a textbook, seminar slide, or generic
  AI side-hustle material.
- The visual would only decorate the text.

Recommend image when:
- The post contains a useful structure that readers may save: 3-part
  decomposition, input/judgment/output sorting, before/after comparison,
  checklist, roadmap, flow, or task classification.
- The image can make a procedure or comparison easier to revisit later.

The image decision should be one of: text_only or image. Prefer text_only unless
save value is clear.
""",
    image_prompt_direction="""\
If generating an image for ai_side_business, create a clean, practical diagram
for non-engineers using AI at work. It should be save-worthy, not decorative.

Use directions such as:
- A simple Japanese infographic showing "AIに渡す前の3分解": input, judgment,
  output, with short labels and generous spacing.
- A before/after workflow diagram showing manual work becoming an AI-assisted
  draft, check, and finish flow.
- A compact checklist or classification table for email drafts, meeting notes,
  work memos, and document rough drafts.

Always keep it restrained, readable on a smartphone, and practical. Avoid
flashy money imagery, luxury imagery, guru/seminar mood, excessive icons,
crowded text, and "AI makes you rich" framing.
""",
    draft_preview_reason=(
        "The draft positions AI as a practical way for non-engineers to lighten "
        "real work and improve small workflows, with Codex practice or concrete "
        "task handoff instead of shady side-hustle claims."
    ),
    image_role=(
        "Optional and strict. Use images only for save-worthy diagrams, "
        "checklists, before/after comparisons, roadmaps, or task classifications."
    ),
    recommended_visual_direction=(
        "Text-only by default. Recommend an image only when a practical diagram "
        "or checklist clearly increases save value for non-engineers using AI at "
        "work."
    ),
)


ACCOUNT_POLICIES: dict[str, AccountPromptPolicy] = {
    YOKAZE_DAILY_POLICY.account_id: YOKAZE_DAILY_POLICY,
    NEW_ACCOUNT_DAILY_POLICY.account_id: NEW_ACCOUNT_DAILY_POLICY,
    AI_SIDE_BUSINESS_POLICY.account_id: AI_SIDE_BUSINESS_POLICY,
    "ai_pickup": AI_SIDE_BUSINESS_POLICY,
}


def get_account_prompt_policy(account_id: str) -> AccountPromptPolicy | None:
    """Return an account-specific prompt policy when one is defined."""

    return ACCOUNT_POLICIES.get(account_id)
