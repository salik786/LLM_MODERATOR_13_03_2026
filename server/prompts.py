from __future__ import annotations

# ============================================================
# 📦 Imports
# ============================================================
from typing import List, Dict, Any, Optional
import os
import re
import logging
import random
import traceback
from dotenv import load_dotenv

# ============================================================
# 🔧 Environment Setup
# ============================================================
load_dotenv()
logger = logging.getLogger("moderator-prompts")

# ============================================================
# ⚙️ Config Loader
# ============================================================
def get_env(name: str, cast=str, required: bool = False):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        msg = f"[Config] Missing env var: {name}"
        if required:
            raise EnvironmentError(msg)
        logger.warning(msg)
        return None
    try:
        return cast(value)
    except Exception:
        logger.error(f"[Config] Failed to cast {name}")
        return None

# ============================================================
# 🌍 Core Model Configuration
# ============================================================
LLM_PROVIDER = get_env("LLM_PROVIDER", str, False) or "groq"
GROQ_MODEL = get_env("GROQ_MODEL", str, False) or "llama-3.1-8b-instant"
GROQ_TEMPERATURE = get_env("GROQ_TEMPERATURE", float, False) or 0.7
GROQ_MAX_TOKENS = get_env("GROQ_MAX_TOKENS", int, False) or 2000

OPENAI_MODEL = get_env("OPENAI_CHAT_MODEL", str, False) or "gpt-4o-mini"
OPENAI_TEMPERATURE = get_env("OPENAI_TEMPERATURE", float, False) or 0.7
OPENAI_MAX_TOKENS = get_env("OPENAI_MAX_TOKENS", int, False) or 2000

CHAT_HISTORY_LIMIT = get_env("CHAT_HISTORY_LIMIT", int, False) or 50
WELCOME_MESSAGE = get_env("WELCOME_MESSAGE", str, False) or "Welcome everyone! I'm the Moderator."

# ============================================================
# 🧠 LLM Client Initialization
# ============================================================
groq_client = None
openai_client = None

# Try to initialize OpenAI if API key exists
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"🔑 OPENAI_API_KEY exists: {bool(openai_api_key)}")
    if openai_api_key and openai_api_key.strip():
        logger.info(f"🔑 OPENAI_API_KEY length: {len(openai_api_key)}")
        logger.info(f"🔑 OPENAI_API_KEY starts with: {openai_api_key[:7]}...")
        from openai import OpenAI
        openai_client = OpenAI(api_key=openai_api_key)
        logger.info("✅ OpenAI client initialized successfully")
        logger.info("✅ OpenAI client ready for API calls")
    else:
        logger.warning("⚠️ OPENAI_API_KEY not found or empty")
except ImportError:
    logger.warning("⚠️ openai package not installed. Run: pip install openai")
except Exception as e:
    logger.error(f"❌ OpenAI client initialization failed: {e}")
    logger.error(traceback.format_exc())

# Try to initialize Groq as fallback
try:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and groq_api_key.strip():
        from groq import Groq
        groq_client = Groq(api_key=groq_api_key)
        logger.info("✅ Groq client initialized as fallback")
    else:
        logger.warning("⚠️ GROQ_API_KEY not found")
except ImportError:
    logger.warning("⚠️ groq package not installed")
except Exception as e:
    logger.error(f"❌ Groq client initialization failed: {e}")

# ============================================================
# 🛠 Helper Functions
# ============================================================
def call_llm(messages, temperature=None, max_tokens=None, system_prompt=None):
    """Make LLM API call (OpenAI preferred, Groq fallback)"""
    
    logger.info("="*50)
    logger.info("📞 call_llm INVOKED")
    logger.info(f"   LLM_PROVIDER setting: {LLM_PROVIDER}")
    logger.info(f"   OpenAI client available: {openai_client is not None}")
    logger.info(f"   Groq client available: {groq_client is not None}")
    logger.info(f"   Temperature: {temperature}")
    logger.info(f"   Max tokens: {max_tokens}")
    logger.info(f"   System prompt provided: {bool(system_prompt)}")
    logger.info(f"   Number of messages: {len(messages) if messages else 0}")
    
    if not openai_client and not groq_client:
        logger.error("❌ No LLM client available - both OpenAI and Groq are None")
        return None
    
    try:
        # ===== OPENAI PATH (Primary) =====
        if LLM_PROVIDER == "openai" and openai_client:
            logger.info("🟢 ATTEMPTING OpenAI API call...")
            
            # Format messages for OpenAI
            openai_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
                logger.debug(f"System prompt (first 100 chars): {system_prompt[:100]}...")
            
            # Add conversation messages
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    openai_messages.append({"role": role, "content": content})
                    logger.debug(f"Message {i}: role={role}, content length={len(content)}")
                else:
                    openai_messages.append({"role": "user", "content": str(msg)})
                    logger.debug(f"Message {i}: (string) content length={len(str(msg))}")
            
            logger.info(f"📤 Sending {len(openai_messages)} messages to OpenAI")
            logger.info(f"   Model: {OPENAI_MODEL}")
            logger.info(f"   Temperature: {temperature or OPENAI_TEMPERATURE}")
            logger.info(f"   Max tokens: {max_tokens or OPENAI_MAX_TOKENS}")
            
            try:
                # Make the API call
                logger.info("⏳ Waiting for OpenAI response...")
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=openai_messages,
                    temperature=temperature or OPENAI_TEMPERATURE,
                    max_tokens=max_tokens or OPENAI_MAX_TOKENS
                )
                
                content = response.choices[0].message.content
                logger.info(f"✅ OpenAI API call SUCCESSFUL!")
                logger.info(f"   Response length: {len(content)} chars")
                logger.info(f"   Response preview: {content[:150]}...")
                return content
                
            except Exception as openai_error:
                logger.error(f"❌ OpenAI API call FAILED: {openai_error}")
                logger.error(f"   Error type: {type(openai_error).__name__}")
                logger.error(f"   Full traceback: {traceback.format_exc()}")
                
                # Check for specific error types
                error_str = str(openai_error).lower()
                if "authentication" in error_str or "api key" in error_str:
                    logger.error("🔑 This appears to be an API KEY issue. Check your OPENAI_API_KEY in .env")
                elif "rate limit" in error_str:
                    logger.error("⏱️ Rate limit exceeded. Try again later.")
                elif "billing" in error_str or "quota" in error_str:
                    logger.error("💰 Billing issue. Check your OpenAI account credits.")
                elif "connection" in error_str:
                    logger.error("🌐 Network connection issue. Check your internet.")
                
                return None
        
        # ===== GROQ PATH (Fallback) =====
        elif groq_client:
            logger.info("🟣 ATTEMPTING Groq API call (fallback)...")
            
            groq_messages = []
            if system_prompt:
                groq_messages.append({"role": "system", "content": system_prompt})
            
            for msg in messages:
                if isinstance(msg, dict):
                    groq_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                else:
                    groq_messages.append({"role": "user", "content": str(msg)})
            
            try:
                response = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=groq_messages,
                    temperature=temperature or GROQ_TEMPERATURE,
                    max_tokens=max_tokens or GROQ_MAX_TOKENS,
                    stream=False,
                )
                
                content = response.choices[0].message.content
                logger.info(f"✅ Groq response received ({len(content)} chars)")
                return content
            except Exception as groq_error:
                logger.error(f"❌ Groq API call failed: {groq_error}")
                return None
        
        else:
            logger.error(f"❌ Requested provider {LLM_PROVIDER} not available")
            logger.error(f"   OpenAI available: {openai_client is not None}")
            logger.error(f"   Groq available: {groq_client is not None}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Unexpected error in call_llm: {e}")
        logger.error(traceback.format_exc())
        return None

def get_fallback_response():
    """Get a simple fallback response"""
    responses = [
        "Thanks for sharing! Let's continue.",
        "I appreciate your input. What do others think?",
        "Good point! Let's keep discussing.",
        "Interesting observation! What do others think?",
        "Let's hear from everyone on this point.",
        "That's an interesting perspective. Any other thoughts?"
    ]
    return random.choice(responses)

# ============================================================
# 🎯 RESEARCH STUDY PROMPTS - DESERT SURVIVAL TASK
# ============================================================
DESERT_ITEMS = [
    "A flashlight (4 battery size)",
    "A map of the region",
    "A compass",
    "A large plastic sheet",
    "A box of matches",
    "A winter coat",
    "A bottle of salt tablets (1000 tablets)",
    "A small knife",
    "2 quarts of water per person",
    "A cosmetic mirror",
    "A parachute (red & white)",
    "A book - 'Edible Animals of the Desert'"
]

def format_items_list():
    """Format items for display in prompts"""
    return "\n".join([f"• {item}" for item in DESERT_ITEMS])

# ============================================================
# 🚫 SLANG/INAPPROPRIATE LANGUAGE DETECTION
# ============================================================
# Only flag genuinely inappropriate content, not normal conversation
INAPPROPRIATE_WORDS = [
    # Profanity
    'stupid', 'dumb', 'idiot', 'moron', 'loser', 
    'shut up', 'shutup', 'crap', 'damn', 'hell',
    # Extremely casual slang that's inappropriate for academic setting
    'wtf', 'omg', 'lol', 'rofl', 'lmfao', 'lmao',
]

# Words that should NEVER trigger a warning (common in conversation)
SAFE_WORDS = [
    'let\'s', 'lets', 'whats', 'what\'s', 'next', 'start', 
    'think', 'thought', 'please', 'thanks', 'thank',
    'help', 'question', 'understand', 'explain', 'good', 'great',
    'interesting', 'point', 'idea', 'agree', 'disagree'
]

def check_inappropriate_language(message: str) -> tuple[bool, List[str]]:
    """Check if message contains genuinely inappropriate language or slang"""
    if not message:
        return False, []
    
    message_lower = message.lower()
    found_words = []
    
    # First, check if it's a safe message (questions about the task)
    if any(word in message_lower for word in ['what', 'how', 'why', 'when', 'where', 'which']):
        # Questions are usually fine, don't warn
        return False, []
    
    # Check for safe words that might contain inappropriate substrings
    for safe in SAFE_WORDS:
        if safe in message_lower:
            return False, []
    
    # Only check for genuinely inappropriate words
    for word in INAPPROPRIATE_WORDS:
        if word in message_lower:
            # Make sure it's a whole word match where appropriate
            if len(word) > 2:  # Avoid flagging short substrings
                found_words.append(word)
    
    return len(found_words) > 0, found_words

# ============================================================
# 🟢 ACTIVE MODERATOR PROMPTS (Research Version)
# ============================================================
ACTIVE_MODERATOR_SYSTEM_PROMPT = """You are an ACTIVE moderator for a 3-person group discussion.

IMPORTANT - THE ONLY PARTICIPANTS IN THIS ROOM ARE:
{participant_list}

You MUST ONLY address these specific participants by their exact names shown above.
Do NOT invent or use any other names like Rachel, Sarah, Michael, etc.

YOUR ROLE:
- Proactively guide the discussion
- Ensure balanced participation
- Invite quieter members by name
- Gently manage dominant speakers
- Keep discussion on track
- Help group reach consensus within time limit
- Answer questions about the task when asked
- Be helpful and encouraging

BEHAVIOR RULES:
1. If someone hasn't spoken in 3 minutes → invite them by name
2. If one person contributes >50% of messages in last 5 minutes → gently ask others for their views
3. Every 5 minutes → provide a brief summary of progress
4. In last 5 minutes → remind group to finalize ranking
5. Answer questions directly and helpfully
6. Always be polite, encouraging, and neutral

TASK: Desert survival ranking
ITEMS TO RANK:
{items}

Remember: You are ACTIVE - you initiate, guide, and balance.
ONLY use these participant names: {participant_list}
"""

PASSIVE_MODERATOR_SYSTEM_PROMPT = """You are a PASSIVE moderator for a 3-person group discussion.

IMPORTANT - THE ONLY PARTICIPANTS IN THIS ROOM ARE:
{participant_list}

You MUST ONLY address these specific participants by their exact names shown above.
Do NOT invent or use any other names.

YOUR ROLE:
- Only speak when directly addressed by participants
- Provide minimal responses
- Do NOT initiate or guide discussion
- Do NOT balance participation
- Only intervene for clear policy violations

BEHAVIOR RULES:
1. ONLY speak if a participant asks you a direct question
2. If asked, give brief, neutral responses (1-2 sentences max)
3. Do NOT invite quiet members
4. Do NOT summarize unless explicitly asked
5. Do NOT manage turn-taking
6. Answer questions about time or task if asked

TASK: Desert survival ranking
ITEMS TO RANK:
{items}

Remember: You are PASSIVE - wait to be asked, respond minimally.
ONLY use these participant names: {participant_list}
"""

# ============================================================
# 💬 ACTIVE MODERATOR RESPONSE GENERATOR
# ============================================================
def generate_active_moderator_response(
    participants: List[str],
    chat_history: List[Dict[str, Any]],
    task_context: str,
    time_elapsed: int,
    last_intervention_time: int,
    dominance_detected: Optional[str] = None,
    silent_user: Optional[str] = None
) -> str:
    """Generate ACTIVE moderator response based on research rules"""
    try:
        logger.info("="*60)
        logger.info("🎯 GENERATE_ACTIVE_MODERATOR_RESPONSE CALLED")
        logger.info(f"   Participants: {participants}")
        logger.info(f"   Chat history length: {len(chat_history)}")
        logger.info(f"   Time elapsed: {time_elapsed} min")
        logger.info(f"   Last intervention: {last_intervention_time}s ago")
        logger.info(f"   Dominance detected: {dominance_detected}")
        logger.info(f"   Silent user: {silent_user}")
        logger.info(f"   LLM Provider from config: {LLM_PROVIDER}")
        logger.info(f"   OpenAI client available: {openai_client is not None}")
        logger.info(f"   Groq client available: {groq_client is not None}")
        
        # Filter out Moderator from participants list
        actual_participants = [p for p in participants if p != 'Moderator' and p]
        logger.info(f"   Actual participants: {actual_participants}")
        
        if not actual_participants:
            logger.warning("⚠️ No actual participants found, returning welcome message")
            return "Welcome to the desert survival task! Please introduce yourselves."
        
        # Check last message for inappropriate language (but don't block questions)
        if chat_history and len(chat_history) > 0:
            last_msg = chat_history[-1]
            last_sender = last_msg.get('sender', '')
            last_content = last_msg.get('message', '')
            logger.info(f"   Last message from {last_sender}: {last_content[:100]}")
            
            # Only check if it's not a question
            if '?' not in last_content:
                is_inappropriate, bad_words = check_inappropriate_language(last_content)
                if is_inappropriate:
                    warning_msg = f"{last_sender}, please keep our discussion professional and academic. Let's focus on the desert survival task."
                    logger.info(f"⚠️ Inappropriate language detected from {last_sender}: {bad_words}")
                    return warning_msg
        
        # Format chat history
        trimmed_history = chat_history[-20:] if chat_history else []
        chat_text = ""
        for msg in trimmed_history:
            sender = msg.get('sender', 'Unknown')
            message = msg.get('message', '')
            # Don't include moderator messages in history for context
            if sender != 'Moderator':
                chat_text += f"{sender}: {message}\n"
        
        logger.info(f"📝 Formatted chat history ({len(trimmed_history)} messages)")
        
        # Build context
        time_remaining = max(0, 15 - time_elapsed)
        logger.info(f"⏱️ Time remaining: {time_remaining} minutes")
        
        # Format participant list for prompt
        participant_list_str = ", ".join(actual_participants)
        
        # Determine intervention type
        intervention_type = "normal"
        
        # First, check if the last message was a question that needs answering
        if chat_history and len(chat_history) > 0:
            last_msg = chat_history[-1]
            if last_msg.get('sender') != 'Moderator':
                last_content = last_msg.get('message', '').lower()
                question_phrases = ['what we have to do', 'what to do', 'what next', 'what\'s next', 'whats next', 
                                   'how to', 'what is the task', 'what should we', 'explain', 'how should i start',
                                   'what do we do', 'help', 'confused', 'not sure']
                
                is_question = any(phrase in last_content for phrase in question_phrases) or '?' in last_content
                logger.info(f"❓ Is last message a question? {is_question}")
                
                if is_question:
                    intervention_type = "answer_question"
                    logger.info(f"📝 Detected question, will answer")
        
        # If not a question, check other intervention types
        if intervention_type == "normal":
            if silent_user and time_elapsed > 3:
                intervention_type = "invite_silent"
                logger.info(f"🤫 Will invite silent user: {silent_user}")
            elif dominance_detected:
                intervention_type = "balance_dominance"
                logger.info(f"👑 Will balance dominance for: {dominance_detected}")
            elif time_remaining <= 5:
                intervention_type = "time_warning"
                logger.info(f"⏰ Will give time warning")
            elif time_elapsed > 0 and time_elapsed % 5 == 0:
                intervention_type = "summarize"
                logger.info(f"📊 Will provide summary")
        
        logger.info(f"🎯 Final intervention type: {intervention_type}")
        
        # Create prompt with ACTUAL participant names
        if intervention_type == "answer_question":
            last_question = chat_history[-1].get('message', '') if chat_history else ''
            prompt = f"""You are an ACTIVE moderator. The participants are: {participant_list_str}

The last user message was: "{last_question}"

Please answer their question helpfully and concisely in 1-2 sentences. 
If they're asking about the task, explain that they need to rank the 12 desert survival items from most important (1) to least important (12).
If they're asking about time, tell them they have {time_remaining} minutes remaining.
ONLY use the actual participant names: {participant_list_str}"""
        
        elif intervention_type == "invite_silent" and silent_user in actual_participants:
            prompt = f"""You are an ACTIVE moderator. The participants are: {participant_list_str}
{silent_user} hasn't spoken in a while. Politely invite them to share their thoughts on the desert survival ranking in 1 sentence.
ONLY use the actual participant names: {participant_list_str}"""
        
        elif intervention_type == "balance_dominance" and dominance_detected in actual_participants:
            other_participants = [p for p in actual_participants if p != dominance_detected]
            prompt = f"""You are an ACTIVE moderator. The participants are: {participant_list_str}
{dominance_detected} has been dominating the conversation. Gently ask {', '.join(other_participants)} for their perspective in 1 sentence.
ONLY use the actual participant names: {participant_list_str}"""
        
        elif intervention_type == "time_warning":
            prompt = f"""You are an ACTIVE moderator. The participants are: {participant_list_str}
Only {time_remaining} minutes left. Remind the group to work towards finalizing their ranking in 1 sentence.
ONLY use the actual participant names: {participant_list_str}"""
        
        elif intervention_type == "summarize":
            prompt = f"""You are an ACTIVE moderator. The participants are: {participant_list_str}
Based on this chat history: {chat_text[:200]}...
Provide a brief summary of their progress so far in 1-2 sentences.
ONLY use the actual participant names: {participant_list_str}"""
        
        else:
            # Normal facilitation
            prompt = f"""You are an ACTIVE moderator. The participants are: {participant_list_str}
Based on this chat history: {chat_text[:200]}...
Provide a natural, helpful facilitation message to keep the discussion moving in 1 sentence.
ONLY use the actual participant names: {participant_list_str}"""
        
        logger.info(f"📝 Prompt created (type: {intervention_type})")
        logger.info(f"   Prompt preview: {prompt[:150]}...")
        
        # Get system prompt with actual participants
        system_prompt = ACTIVE_MODERATOR_SYSTEM_PROMPT.format(
            participant_list=participant_list_str,
            items=format_items_list()
        )
        logger.info(f"📝 System prompt created, length: {len(system_prompt)} chars")
        
        logger.info(f"📤 About to call call_llm...")
        
        # Call LLM with proper parameters
        response = call_llm(
            messages=[
                {"role": "user", "content": prompt}
            ],
            system_prompt=system_prompt,
            temperature=0.7 if intervention_type == "normal" else 0.5,
            max_tokens=150
        )
        
        if response:
            logger.info(f"✅ Received response from LLM, length: {len(response)} chars")
            text = response.strip()
            # Remove any "Moderator:" prefix if present
            text = re.sub(r"^\s*Moderator[:\-–]?\s*", "", text)
            
            # Final check: ensure no fake names are used
            words = text.split()
            fake_name_detected = False
            for word in words:
                clean_word = word.strip('.,!?\'"()[]{}')
                if clean_word and clean_word[0].isupper() and clean_word not in actual_participants:
                    # Comprehensive list of common English words
                    common_words = [
                        'I', 'We', 'You', 'They', 'He', 'She', 'It', 'The', 'This', 'That', 'These', 'Those',
                        'Let', 'Let\'s', 'Lets', 'Id', 'I\'d', 'Ill', 'I\'ll', 'Im', 'I\'m', 'Ive', 'I\'ve',
                        'We\'re', 'We\'ll', 'We\'ve', 'We\'d', 'You\'re', 'You\'ll', 'You\'ve', 'You\'d',
                        'Please', 'Thanks', 'Thank', 'Good', 'Great', 'Awesome', 'Interesting',
                        'What', 'How', 'Why', 'When', 'Where', 'Which', 'Who', 'Whom',
                        'Next', 'Start', 'Begin', 'Think', 'Thought', 'Help', 'Question', 'Answer',
                        'Point', 'Idea', 'Agree', 'Disagree', 'Hello', 'Hi', 'Hey', 'Welcome',
                        'Everyone', 'All', 'Some', 'Most', 'Few', 'Many', 'Both', 'Each', 'Every',
                        'First', 'Second', 'Third', 'Last', 'Final', 'Important', 'Critical',
                        'Water', 'Desert', 'Survival', 'Item', 'Items', 'Rank', 'Ranking',
                        'Mirror', 'Flashlight', 'Knife', 'Parachute', 'Compass', 'Map', 'Matches',
                        'Coat', 'Plastic', 'Sheet', 'Book', 'Salt', 'Tablets', 'Bottle',
                        'Student', 'Students', 'Group', 'Team', 'Everyone'
                    ]
                    if clean_word not in common_words and len(clean_word) > 2:
                        logger.warning(f"⚠️ Detected potential fake name '{clean_word}', using fallback")
                        fake_name_detected = True
                        break
            
            if fake_name_detected:
                return get_fallback_response()
            
            logger.info(f"✅ Final response: {text[:150]}...")
            return text
        
        logger.warning("⚠️ No response from LLM, using fallback")
        return get_fallback_response()
            
    except Exception as e:
        logger.error(f"❌ [generate_active_moderator_response] Error: {e}")
        logger.error(traceback.format_exc())
        return get_fallback_response()

# ============================================================
# 💬 PASSIVE MODERATOR RESPONSE GENERATOR - ADD THIS FUNCTION
# ============================================================
def generate_passive_moderator_response(
    participants: List[str],
    chat_history: List[Dict[str, Any]],
    last_user_message: Optional[str] = None,
    time_elapsed: int = 0
) -> Optional[str]:
    """Generate PASSIVE moderator response - ONLY when asked directly"""
    try:
        if not last_user_message:
            return None
        
        # Filter out Moderator
        actual_participants = [p for p in participants if p != 'Moderator' and p]
        
        last_msg_lower = last_user_message.lower()
        time_remaining = max(0, 15 - time_elapsed)
        
        # Check if moderator was asked directly
        asked_moderator = any([
            '@moderator' in last_msg_lower,
            'moderator' in last_msg_lower and '?' in last_user_message,
            'what do you think' in last_msg_lower,
            'your opinion' in last_msg_lower,
            'help us' in last_msg_lower,
            'can you help' in last_msg_lower,
            'what should we' in last_msg_lower
        ])
        
        if not asked_moderator:
            return None
        
        # Simple, minimal response based on question type
        if 'time' in last_msg_lower or 'minute' in last_msg_lower:
            return f"You have about {time_remaining} minutes remaining."
        elif 'rank' in last_msg_lower or 'item' in last_msg_lower or 'task' in last_msg_lower:
            return "You need to rank the 12 desert survival items from most important (1) to least important (12)."
        else:
            return "I'm observing the discussion. Continue with your task."
            
    except Exception as e:
        logger.error(f"❌ [generate_passive_moderator_response] Error: {e}")
        return None

# ============================================================
# ✅ FEEDBACK GENERATION
# ============================================================
def generate_personalized_feedback(
    student_name: str,
    message_count: int,
    response_times: List[float],
    story_progress: int,
    hint_responses: int = 0,
    behavior_type: str = "moderate",
    toxic_count: int = 0,
    off_topic_count: int = 0,
    chat_history: List[Dict[str, Any]] = None,
    story_context: str = ""
) -> str:
    """Generate detailed feedback with Strengths, Areas for Improvement, and Next Steps."""
    try:
        student_messages = []
        if chat_history:
            student_messages = [msg.get('message', '') for msg in chat_history if msg.get('sender') == student_name]
        
        # Check for inappropriate language in student's messages
        inappropriate_count = 0
        if student_messages:
            for msg in student_messages:
                is_inappropriate, _ = check_inappropriate_language(msg)
                if is_inappropriate:
                    inappropriate_count += 1
        
        if student_messages:
            messages_text = "\n".join([f"- {msg}" for msg in student_messages[-5:]])
            logger.info(f"📝 Found {len(student_messages)} messages from {student_name}")
        else:
            messages_text = "No messages sent."
        
        # Use OpenAI for feedback if available
        if openai_client and LLM_PROVIDER == "openai":
            prompt = f"""You are an expert educational facilitator providing personalized feedback.

STUDENT: {student_name}
MESSAGES SENT: {message_count}
PROGRESS: {story_progress}%
INAPPROPRIATE LANGUAGE COUNT: {inappropriate_count}

STUDENT'S MESSAGES:
{messages_text}

Write feedback with:
1. "Hi {student_name}," on its own line
2. Warm opening acknowledging their contribution
3. **Strengths:** (2-3 bullet points)
4. **Areas for Improvement:** (1-2 bullet points, include note about professional language if inappropriate_count > 0)
5. **Next Steps:** (1-2 bullet points)
6. Encouraging closing

Use bullet points with * or -.

FEEDBACK:"""
            
            response = call_llm(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system_prompt="You are a warm, supportive teacher giving structured feedback.",
                temperature=0.7,
                max_tokens=600
            )
            
            if response and len(response.strip()) > 50:
                return f"\n📊 **Your Feedback**\n\n{response.strip()}"
        
        # Fallback to template-based feedback
        return generate_detailed_fallback(student_name, message_count, student_messages, inappropriate_count)
            
    except Exception as e:
        logger.error(f"❌ Error generating feedback: {e}")
        return generate_detailed_fallback(student_name, message_count, student_messages if 'student_messages' in locals() else [], 0)

def generate_detailed_fallback(student_name: str, message_count: int, student_messages: List[str] = None, inappropriate_count: int = 0) -> str:
    """Fallback feedback when LLM is unavailable"""
    student_messages = student_messages or []
    last_message = student_messages[-1][:100] + "..." if student_messages else "participating"
    
    inappropriate_note = ""
    if inappropriate_count > 0:
        inappropriate_note = "\n• Remember to keep language professional and academic"
    
    if message_count == 0:
        return f"""
📊 **Your Feedback**

Hi {student_name},

Thank you for being part of our session today.

**Strengths:**
• You showed up and engaged silently

**Areas for Improvement:**
• Try sharing one small thought next time{inappropriate_note}

**Next Steps:**
• Start with one observation next session

I look forward to hearing from you!
"""
    elif message_count <= 2:
        return f"""
📊 **Your Feedback**

Hi {student_name},

Thank you for your contributions!

**Strengths:**
• You were willing to participate
• Your message about "{last_message}" showed engagement

**Areas for Improvement:**
• Try to elaborate more on your ideas{inappropriate_note}

**Next Steps:**
• Try to share 2-3 times next session

Keep up the good work!
"""
    else:
        return f"""
📊 **Your Feedback**

Hi {student_name},

Thank you for your active participation!

**Strengths:**
• You consistently engaged with the material
• Your message about "{last_message}" showed creative thinking

**Areas for Improvement:**
• Try connecting your ideas to what others said{inappropriate_note}

**Next Steps:**
• Build on classmates' ideas

Great work today!
"""

# ============================================================
# 🍃 RANDOM ENDINGS
# ============================================================
def get_random_ending() -> str:
    """Return a random ending message for sessions"""
    endings = [
        "The discussion has concluded. Thank you for participating!",
        "Great discussion everyone! The session is now complete.",
        "Thank you for your valuable contributions to this session.",
        "Session completed. Great work collaborating with your team!",
        "The desert survival task is now complete. Well done everyone!"
    ]
    return random.choice(endings)