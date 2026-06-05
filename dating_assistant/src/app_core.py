from __future__ import annotations

from .conversation_planner import build_strategy, estimate_partner_temperature, estimate_stage
from .flirt import allowed_flirt_level
from .invite_generator import maybe_generate_invite
from .loaders import load_config
from .message_generator import generate_messages, generate_reply
from .models import GenerationRequest, GenerationResult
from .profile_analyzer import analyze_profile
from .safety_reviewer import SafetyReviewer
from .topic_matcher import match_topics


def generate(request: GenerationRequest) -> GenerationResult:
    topic_scores = load_config("topic_scores.yaml").get("topic_scores", {})
    flirt_policy = load_config("flirt_policy.yaml")
    safety_policy = load_config("safety_policy.yaml")
    reply_topic_policy = load_config("reply_topic_policy.yaml")

    stage = estimate_stage(request.conversation_history, request.current_stage)
    request.current_stage = stage
    topics = match_topics(request.target_profile, request.user_profile, topic_scores)
    level = allowed_flirt_level(flirt_policy, stage, request.desired_flirt_level)
    temperature = estimate_partner_temperature(request.conversation_history)

    if request.purpose == "reply":
        candidates = generate_reply(request, topics["common"], level, reply_topic_policy, temperature)
    else:
        candidates = generate_messages(request, topics["common"], topics["light"], level)

    reviewer = SafetyReviewer(safety_policy)
    reviewed = [(candidate, reviewer.review(candidate, request.conversation_history)) for candidate in candidates]
    best = next((message for message, review in reviewed if review["status"] == "OK"), reviewed[0][0])
    best_review = reviewer.review(best, request.conversation_history)
    invite = maybe_generate_invite(request, temperature) if request.purpose == "invite" else None

    return GenerationResult(
        partner_analysis=analyze_profile(request.target_profile),
        compatibility_topics=topics["common"],
        safe_topics=topics["common"],
        light_only_topics=topics["light"],
        avoid_topics=topics["avoid"] + topics["deep_caution"],
        recommended_strategy=build_strategy(topics["common"], topics["light"], topics["avoid"], stage),
        message_candidates=candidates,
        best_message=best,
        invite_suggestion=invite,
        flirt_allowed_level=level,
        safety_notes=list(best_review["notes"]),
        ng_examples=list(best_review["ng_examples"]),
        partner_temperature=temperature,
    )
