from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .models import PartnerRecord
from .partner_manager import save_updated_partner
from .partner_store import load_partner
from .suggestion_manager import add_suggestion

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
_USER_PROFILE_PATH = Path(__file__).resolve().parents[1] / "data" / "local" / "user_profile.json"


def _get_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    return None


def is_api_key_configured() -> bool:
    return bool(_get_api_key())


def _load_user_profile_data() -> dict:
    if not _USER_PROFILE_PATH.exists():
        return {}
    try:
        data = json.loads(_USER_PROFILE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_user_name() -> str:
    return str(_load_user_profile_data().get("name", "") or "")


def _build_system_prompt(
    partner: PartnerRecord,
    tone: str,
    objectives: list[str],
    supplement_notes: list[str] | None = None,
    style_samples: list[str] | None = None,
) -> str:
    partner_name = partner.display_name or "相手"
    profile_text = partner.profile.profile_text or "プロフィール情報なし"
    user_name = _load_user_name()

    # B(a): 直近10件制限を撤廃し、重複話題・既出質問を確実に検出できるよう履歴を広く渡す。
    # テキスト会話ならトークン的に問題ないが、暴走防止に上限だけ設ける。
    conversation_lines = []
    for turn in partner.conversation[-80:]:
        label = "ユーザー" if turn.speaker == "user" else f"相手（{partner_name}）"
        conversation_lines.append(f"{label}: {turn.text}")
    conversation_history = "\n".join(conversation_lines) if conversation_lines else "会話履歴なし"

    last_partner_message = ""
    for turn in reversed(partner.conversation):
        if turn.speaker == "partner":
            last_partner_message = turn.text
            break

    style_parts = []
    if tone:
        style_parts.append(f"雰囲気: {tone}")
    if objectives:
        style_parts.append("目的: " + "、".join(objectives))
    reply_style = "、".join(style_parts) if style_parts else "自然な返信"

    last_message_section = (
        f"【最新の相手のメッセージ】\n{last_partner_message}\n\n"
        if last_partner_message else ""
    )

    user_name_line = f"- ユーザーの名前: {user_name}\n" if user_name else ""

    # 自分（ユーザー）の詳細プロフィールをプロンプト冒頭に組み込む
    user_profile_data = _load_user_profile_data()
    user_profile_fields = [
        ("名前", str(user_profile_data.get("name", "") or "").strip()),
        ("職業", str(user_profile_data.get("occupation", "") or "").strip()),
        ("仕事のスケジュール", str(user_profile_data.get("work_schedule", "") or "").strip()),
        ("趣味・好きなこと", str(user_profile_data.get("hobbies", "") or "").strip()),
        ("苦手・知らないこと", str(user_profile_data.get("not_good_at", "") or "").strip()),
        ("生活スタイル・性格", str(user_profile_data.get("lifestyle", "") or "").strip()),
        ("デートの好み", str(user_profile_data.get("date_preferences", "") or "").strip()),
    ]
    user_profile_lines = [f"- {label}: {value}" for label, value in user_profile_fields if value]
    user_profile_section = (
        "## 自分（ユーザー）のプロフィール\n"
        "（返信文は必ずこの情報を踏まえて生成すること。自分が知らないこと・できないことは絶対に返信に含めない）\n\n"
        + "\n".join(user_profile_lines)
        + "\n\n"
        "特に「苦手・知らないこと」に書かれた内容は、返信文に含めてはいけない。\n"
        "例：お酒が飲めない場合、お酒の話題を振ったり、お酒が好きと書いてはいけない。\n\n"
    ) if user_profile_lines else ""

    active_notes = [note.strip() for note in (supplement_notes or []) if note and note.strip()]
    supplement_section = (
        "## 重要な補足情報（必ずこの内容を守って文章を生成してください）\n"
        + "\n".join(f"- {note}" for note in active_notes)
        + "\n\n"
    ) if active_notes else ""

    # A) 会話履歴から自分（ユーザー）の発言だけを自動抽出（直近20件中から最大5件）
    own_messages = [
        turn.text.strip()
        for turn in partner.conversation[-20:]
        if turn.speaker == "user" and turn.text.strip()
    ][-5:]
    own_messages_section = (
        "## 自分の過去の発言（文体・言い回しの参考）\n"
        "（以下は自分が実際に送ったメッセージです。同じような文体・テンポ・言い回しで返信を作ってください）\n"
        + "\n".join(f"- {message}" for message in own_messages)
        + "\n\n"
    ) if own_messages else ""

    # B) 手動登録した文体サンプル
    active_styles = [sample.strip() for sample in (style_samples or []) if sample and sample.strip()]
    style_samples_section = (
        "## 自分らしい表現・言い回しのサンプル\n"
        "（以下のような言い回し・テンポ・雰囲気を参考にして返信を作ってください）\n"
        + "\n".join(f"- {sample}" for sample in active_styles)
        + "\n\n"
    ) if active_styles else ""

    # B(b) 既に聞いた質問を抽出（自分の発言のうち「？」を含むもの）。
    # 3候補いずれもこのリストの質問を繰り返さないよう、別枠で明示する。
    own_questions = [
        turn.text.strip()
        for turn in partner.conversation
        if turn.speaker == "user"
        and turn.text.strip()
        and ("？" in turn.text or "?" in turn.text)
    ]
    own_questions_section = (
        "## 既に聞いた質問（3候補いずれも繰り返し禁止）\n"
        "（以下は自分が過去に相手へ聞いた質問です。同じ質問はもちろん、"
        "内容が同じ言い換え・同じカテゴリの質問も繰り返さないこと）\n"
        + "\n".join(f"- {question}" for question in own_questions)
        + "\n\n"
    ) if own_questions else ""

    # C) 相手の温度感（partner.analysis.partner_temperature）を候補2・3の踏み込み度に反映する。
    # 注: 過去に送った文への相手の食いつき記録（sent_records）は現状GUIから保存されないため未使用。
    #     将来GUIが送信済み結果を保存するようになれば、刺さった話題を候補2の新規話題の材料に渡せる。
    temperature = partner.analysis.partner_temperature or "unknown"
    temperature_display = {
        "very_good": "とても良い（相手の食いつきが良い）",
        "good": "良い",
        "normal": "普通",
        "low": "低い（そっけない・短い返信が続く）",
        "unknown": "不明",
    }.get(temperature, temperature)
    if temperature in {"very_good", "good"}:
        temperature_guidance = (
            "- 相手の食いつきが良いので、候補2・候補3は一歩踏み込む・会話を盛り上げる方向で少し攻める。\n"
        )
    elif temperature == "low":
        temperature_guidance = (
            "- 相手の温度感は低めなので、候補2・候補3は軽め・返信しやすい・"
            "プレッシャーの少ない方向にする。重い質問や踏み込みは避ける。\n"
        )
    else:
        temperature_guidance = ""
    temperature_section = (
        "## 相手の温度感（返信の踏み込み度の参考）\n"
        f"- 現在の温度感: {temperature_display}\n"
        f"{temperature_guidance}"
        "\n"
    )

    return (
        "あなたはマッチングアプリでメッセージを送るユーザーの返信を考えるアシスタントです。\n\n"
        f"{user_profile_section}"
        "【重要な前提】\n"
        "- ユーザー（あなたが返信を考える人）: 会話履歴で「ユーザー:」と書かれた発言をしている人\n"
        f"{user_name_line}"
        f"- 相手（マッチングした人）の名前: {partner_name}\n"
        f"- 相手のプロフィール情報: {profile_text}\n\n"
        f"{supplement_section}"
        f"{own_messages_section}"
        f"{style_samples_section}"
        f"{own_questions_section}"
        f"{temperature_section}"
        f"【会話履歴（上が古く、下が最新）】\n{conversation_history}\n\n"
        f"{last_message_section}"
        f"【返信スタイル】\n{reply_style}\n\n"
        "【タスク】\n"
        f"最新の相手のメッセージに対して、ユーザーが{partner_name}さんへ送る返信候補を3つ考えてください。\n"
        "3つの候補は、それぞれ下記の異なる役割（話題と戦略）を必ず担ってください。\n"
        "3候補が同じ話題・同じ切り口に偏ることは禁止します。\n\n"
        "【3候補の役割（話題も戦略も互いに重複させないこと）】\n"
        "■候補1：共感・深掘り（安全）\n"
        "- 相手の直前の発言に乗り、共感＋軽い自己開示をしてから、その話題を深掘りする質問を1つ返す。\n"
        "- 会話の自然な流れを保つ、最も無難な返し。\n"
        "■候補2：新規話題・ユーモア（マンネリ打破）\n"
        "- 相手の直前の話題・相手の趣味とは別の切り口を、新しく振る。\n"
        "- ユーモアや軽い意外性を持たせる。同じ話題ばかりになるのを打破する主役。\n"
        "- 候補1と同じ話題にしないこと。\n"
        "■候補3：柔軟（状況に応じて最適な方向を1つ選ぶ）\n"
        "- 会話の状況を見て、次のいずれか最も効果的な方向を1つだけ選ぶ:\n"
        "  (a) 関係を進める布石（今度〜につなげる） / (b) もっと相手を知る踏み込んだ質問 / (c) 面白さ・意外性重視\n"
        "- ただし候補1・候補2と、話題も戦略も重複しないこと。\n\n"
        "※3候補は書き出し（冒頭の一文）の表現も互いに変えること。3つとも同じ出だし・同じ受けの言い回しで始めない。\n\n"
        "【共通ルール】\n"
        "- 返信はユーザー視点で書く（相手に送るメッセージとして書く）\n"
        "- 自然な会話の流れを維持する\n"
        "- マークダウン記号（#、*、---）は使わない\n"
        "- 候補1:・候補2:・候補3: 以外の見出しは書かない\n"
        "- 各候補は1〜3文程度\n"
        "- 自分のプロフィールに書かれていない知識・経験・趣味は絶対に返信に含めない\n"
        "- 特に「苦手・知らないこと」に書かれた内容は話題にしない・質問しない・知っているふりをしない\n"
        "- 絵文字は1〜2個まで、自然な位置に使う\n"
        "- 質問を入れる場合は各候補で1つまで（複数の質問を一度に投げない）\n"
        "- 「既に聞いた質問」に挙がっている質問・その言い換え・同じカテゴリの質問は、3候補いずれも繰り返さない\n"
        "- 相手が知らない・苦手な話題（苦手リスト）については質問しない\n"
        "- 相手から誘いや提案があった場合は、候補のどれかで日程・時間・段取りの話に進める\n\n"
        "【会話の流れを読む】\n"
        "- 相手のメッセージの意図・感情を読み取り、その流れに沿った返信をする\n"
        "- 相手が疲れていそう・大変そう → 共感・労いを先に入れる\n"
        "- 相手が嬉しそう → 一緒に喜ぶ・盛り上がる\n"
        "- 既に詳しく聞いた話題 → 掘り下げず別の話題へ移す（特に候補2）\n\n"
        "【日常会話の取り入れ方（特に候補2の新規話題で活用）】\n"
        "- 天気・季節、仕事終わりの疲れ・週末の予定、最近見たドラマ/映画、食べたいもの・行きたいお店、"
        "日常のあるある、などプロフィール外の日常的な話題も積極的に使う\n"
        "- 毎回プロフィールの話題だけにならないようにする\n"
        "- 自分の日常も少し交えて親近感を出す\n\n"
        "以下の形式で返してください。\n\n"
        "候補1:\n"
        "（返信文）\n\n"
        "候補2:\n"
        "（返信文）\n\n"
        "候補3:\n"
        "（返信文）\n"
    )


def _parse_candidates(response_text: str) -> list[str]:
    # D: 「候補N:」形式で分割し、取れた分だけ返す（最大3件）。
    # 形式が崩れて1件も取れなかった場合のみ、応答全文を1候補として返すフォールバックを残す。
    # 返り値の件数が3未満なら呼び出し側が不足を検知できる（呼び出し側で candidate_count として返す）。
    parts = re.split(r"候補[１-３1-3]\s*[:：]", response_text)
    candidates = [p.strip() for p in parts[1:] if p.strip()]
    return candidates[:3] if candidates else [response_text.strip()]


def _parse_like_messages(response_text: str) -> list[str]:
    parts = re.split(r"パターン[１-３1-3]\s*[:：]", response_text)
    messages = [p.strip() for p in parts[1:] if p.strip()]
    return messages[:3] if messages else [response_text.strip()]


def generate_like_message(
    partner_id: str,
    tone: str = "自然・普通",
) -> list[str]:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "APIキーが設定されていません。"
            ".envファイルにANTHROPIC_API_KEYを設定してください。"
        )

    try:
        import anthropic
    except ImportError:
        raise ValueError(
            "anthropicライブラリがインストールされていません。"
            "pip install anthropic を実行してください。"
        )

    partner = load_partner(partner_id)
    partner_profile = partner.profile.profile_text or "プロフィール情報なし"

    system_prompt = (
        "あなたはマッチングアプリのいいね文言を考えるアシスタントです。\n\n"
        "【相手のプロフィール】\n"
        f"{partner_profile}\n\n"
        "【文言のトーン】\n"
        f"{tone}\n\n"
        "以下の条件でいいね文言を3パターン考えてください。\n\n"
        "条件:\n"
        "- 40〜100文字程度\n"
        "- 相手のプロフィールの具体的な内容に触れる\n"
        "- テンプレート感がない自然な文章\n"
        "- 質問で終わると返信率が上がる\n"
        "- 褒めすぎない・重たくない\n"
        "- マークダウン記号は使わない\n"
        "- 絵文字は1〜2個まで\n\n"
        "避けること:\n"
        "- 「プロフィール見て気になりました」等のテンプレート表現\n"
        "- 外見への言及\n"
        "- 重たい・長すぎる文章\n\n"
        "以下の形式で返してください。\n\n"
        "パターン1:\n"
        "（文言）\n\n"
        "パターン2:\n"
        "（文言）\n\n"
        "パターン3:\n"
        "（文言）\n"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": "いいね文言を3パターン生成してください。"}],
            system=system_prompt,
        )
        response_text = message.content[0].text
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            raise ValueError(
                "APIキーが正しくありません。.envファイルのANTHROPIC_API_KEYを確認してください。"
            )
        if "rate_limit" in error_msg.lower():
            raise ValueError(
                "APIのレート制限に達しました。しばらく待ってから再試行してください。"
            )
        if "overload" in error_msg.lower():
            raise ValueError(
                "APIサーバーが一時的に混雑しています。しばらく待ってから再試行してください。"
            )
        raise ValueError(f"API呼び出しに失敗しました: {error_msg}")

    return _parse_like_messages(response_text)


def generate_reply_candidates_for_gui(
    partner_id: str,
    objectives: list[str] | None = None,
    tone: str = "自然",
    place_hint: str = "",
    supplement_notes: list[str] | None = None,
    style_samples: list[str] | None = None,
) -> dict[str, Any]:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "APIキーが設定されていません。"
            ".envファイルにANTHROPIC_API_KEYを設定してください。"
        )

    try:
        import anthropic
    except ImportError:
        raise ValueError(
            "anthropicライブラリがインストールされていません。"
            "pip install anthropic を実行してください。"
        )

    partner = load_partner(partner_id)
    selected_objectives = [o for o in (objectives or []) if o]
    all_objectives = selected_objectives[:]
    if place_hint:
        all_objectives.append(f"場所: {place_hint}")

    system_prompt = _build_system_prompt(
        partner,
        tone,
        all_objectives,
        supplement_notes=supplement_notes,
        style_samples=style_samples,
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": "返信候補を3件生成してください。"}],
            system=system_prompt,
        )
        response_text = message.content[0].text
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            raise ValueError(
                "APIキーが正しくありません。.envファイルのANTHROPIC_API_KEYを確認してください。"
            )
        if "rate_limit" in error_msg.lower():
            raise ValueError(
                "APIのレート制限に達しました。しばらく待ってから再試行してください。"
            )
        if "overload" in error_msg.lower():
            raise ValueError(
                "APIサーバーが一時的に混雑しています。しばらく待ってから再試行してください。"
            )
        raise ValueError(f"API呼び出しに失敗しました: {error_msg}")

    raw_candidates = _parse_candidates(response_text)

    mode = "first" if not partner.conversation else "reply"
    purpose = "first" if mode == "first" else "reply"
    # 3候補の役割（_build_system_prompt の【3候補の役割】と対応させる）
    title_labels = ["候補1", "候補2", "候補3"]
    use_cases = ["共感・深掘り", "新規話題・ユーモア", "柔軟（状況に応じて）"]
    aims = [
        "相手の話に共感して自然に深掘りする",
        "別の切り口で新しい話題を振る（マンネリ打破）",
        "状況を見て最適な一手を選ぶ",
    ]

    variants = []
    for index, text in enumerate(raw_candidates):
        suggestion = add_suggestion(partner, purpose=purpose, text=text, source="claude-api")
        variants.append({
            "suggestion_id": suggestion.suggestion_id,
            "text": suggestion.text,
            "purpose": suggestion.purpose,
            "objective": selected_objectives[index % len(selected_objectives)] if selected_objectives else "自然な返信",
            "tone": tone or "自然",
            "title": title_labels[index % len(title_labels)],
            "use_case": use_cases[index % len(use_cases)],
            "aim": aims[index % len(aims)],
            "conversation_stage": "-",
            "temperature": "-",
            "compatibility": "-",
            "next_recommendation": "-",
            "partner_notes": "-",
            "recent_sent_outcomes": [],
            "safety_notes": [],
            "quality_check": [],
        })

    if mode == "first":
        partner.status = "first_message_suggested"
    elif partner.status in {"new_profile", "first_message_sent", "first_message_suggested"}:
        partner.status = "chatting"
    save_updated_partner(partner)

    # D: 取れた候補が3件揃わなかった場合に呼び出し側が不足を検知できるよう件数を返す。
    return {
        "mode": mode,
        "variants": variants,
        "candidate_count": len(raw_candidates),
        "expected_count": 3,
    }
