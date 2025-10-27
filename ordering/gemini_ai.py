import os
from django.conf import settings
import logging

try:
    import google.generativeai as genai
except Exception:  # package may not be installed yet
    genai = None

class KFCGeminiAI:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
        model_name = os.getenv('GEMINI_MODEL') or getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
        self.model = None
        if genai and api_key:
            try:
                genai.configure(api_key=api_key)
                # Try requested model first
                try:
                    self.model = genai.GenerativeModel(model_name)
                except Exception as e:
                    # Attempt dynamic fallback by selecting a supported model
                    if getattr(settings, 'DEBUG', False):
                        logging.getLogger(__name__).warning('Requested Gemini model "%s" failed to initialize (%s). Attempting fallback via list_models...', model_name, e)
                    self.model = self._fallback_model()
            except Exception as e:
                if getattr(settings, 'DEBUG', False):
                    logging.getLogger(__name__).exception('Failed to configure Gemini client: %s', e)
                self.model = None

    def _fallback_model(self):
        try:
            models = list(genai.list_models())
            # Filter models that support text generation
            capable = [m for m in models if 'generateContent' in getattr(m, 'supported_generation_methods', [])]
            # Prefer flash variants for free/fast usage
            prefs = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro', 'gemini-1.0-pro']
            # Normalize model names
            def mname(m):
                return getattr(m, 'name', '')
            chosen = None
            for p in prefs:
                for m in capable:
                    if p in mname(m):
                        chosen = mname(m)
                        break
                if chosen:
                    break
            if not chosen and capable:
                chosen = mname(capable[0])
            if chosen:
                if getattr(settings, 'DEBUG', False):
                    logging.getLogger(__name__).info('Using fallback Gemini model: %s', chosen)
                # API expects full model name, which may already be prefixed like "models/..."
                # google-generativeai accepts either short or full name depending on version; pass the returned name.
                return genai.GenerativeModel(chosen)
        except Exception as e:
            if getattr(settings, 'DEBUG', False):
                logging.getLogger(__name__).exception('Fallback model discovery failed: %s', e)
        return None

    def _extract_text(self, resp):
        # Try standard .text first
        try:
            txt = getattr(resp, 'text', None)
            if txt:
                return txt
        except Exception:
            pass
        # Fallback: aggregate text from candidates/parts
        try:
            texts = []
            for cand in getattr(resp, 'candidates', []) or []:
                parts = getattr(getattr(cand, 'content', None), 'parts', []) or []
                for p in parts:
                    t = getattr(p, 'text', None)
                    if t:
                        texts.append(t)
            return "\n".join(texts) if texts else None
        except Exception:
            return None

    def _safe_generate(self, prompt, fallback):
        if not self.model:
            return fallback
        try:
            resp = self.model.generate_content(prompt)
            text = self._extract_text(resp)
            if not text and getattr(settings, 'DEBUG', False):
                logging.getLogger(__name__).warning('Gemini response had no text; using fallback. Raw: %s', getattr(resp, 'candidates', None))
            return text or fallback
        except Exception as e:
            if getattr(settings, 'DEBUG', False):
                logging.getLogger(__name__).exception('Gemini generate_content failed: %s', e)
            return fallback

    def _tidy(self, text, max_chars=800):
        try:
            t = (text or '').strip()
            # Collapse excessive whitespace
            t = "\n".join(line.strip() for line in t.splitlines() if line.strip())
            if len(t) > max_chars:
                t = t[:max_chars].rstrip() + '…'
            return t
        except Exception:
            return text

    def analyze_kfc_order(self, order_data):
        prompt = f"""
        Role: Friendly, senior QSR analyst for a fried-chicken chain.
        Input: {order_data}
        Task: Produce a brief, KIND, and human summary in PLAIN TEXT (no markdown/ but add emojis), max 100 words.
        Tone: Encouraging, positive, clear. Use everyday language ("Looks good", "Consider").
        Format exactly:
        Validation: <short check>
        Popular: <1-2 items>
        Customer: <1 funny and friendly observation>
        Avoid jargon. Keep it helpful.
        """
        result = self._safe_generate(prompt, "KFC Order Analysis: Order processed successfully.")
        return self._tidy(result, max_chars=600)

    def generate_kfc_receipt(self, order_data):
        prompt = f"""
        Create a concise, warm receipt summary in PLAIN TEXT (no markdown/emojis), max 120 words.
        Input: {order_data}
        Format:
        KFC Receipt
        Items: <name x qty - price, comma separated>
        Total: <amount>
        Note: A short friendly thank-you add come back sugestion
        """
        result = self._safe_generate(prompt, "Thank you for choosing KFC! Your order is being prepared with care.")
        return self._tidy(result, max_chars=700)

    def generate_kfc_business_report(self, sales_data, period='weekly'):
        prompt = f"""
        Produce a compact business snapshot for a fried-chicken chain in PLAIN TEXT, max 150 words, with a constructive and supportive tone.
        Period: {period}
        Data: {sales_data}
        Structure:
        Summary: <1-2 lines>
        Wins: <1 line>
        Risks: <1 line>
        Actions: <3 short bullets>
        """
        result = self._safe_generate(prompt, "KFC Business Report: Data analysis unavailable.")
        return self._tidy(result, max_chars=900)

    def chat_about_system(self, question, history=None):
        """
        Provide a general-purpose chatbot answer about this KFC ordering system.
        History is a list of dicts like {"role": "user"|"assistant", "content": "..."}.
        """
        # Build a compact conversational context to keep prompts short and robust
        sys_preamble = (
            "You are a helpful assistant for a Django + MongoEngine KFC ordering web app. "
            "Answer clearly in plain text. Be concise. If you lack real-time data or a feature, say so briefly."
        )
        convo = []
        try:
            for turn in (history or [])[-6:]:  # last few turns
                role = turn.get('role', 'user')
                content = (turn.get('content') or '').strip()
                if content:
                    convo.append(f"{role.capitalize()}: {content}")
        except Exception:
            pass
        convo_text = "\n".join(convo)
        prompt = f"""
        {sys_preamble}

        Conversation so far:
        {convo_text}

        User: {question}
        Assistant: """
        fallback = "I'm here to help with the KFC ordering system. Please rephrase your question."
        result = self._safe_generate(prompt, fallback)
        return self._tidy(result, max_chars=900)

    def chat_about_menu(self, question, catalog, history=None):
        """
        Strictly answer about available products, their categories, and prices using the provided catalog.
        catalog: list of dicts with keys: name, category, price (number)
        """
        sys_rules = (
            "You are a friendly, concise KFC menu assistant. "
            "Only answer about the provided products, categories, and prices. "
            "Respond directly to the user's question first, in plain text, with a warm and polite tone. "
            "If the user greets or is vague (e.g., 'hi', 'hello', 'yes', 'okay'), give a SHORT helpful overview: "
            "- Mention main categories available. "
            "- List 3–6 representative items with prices (picked from the catalog). "
            "- End with ONE short follow-up question to narrow preference (e.g., category or price range). "
            "Avoid repeated back-and-forth without giving information. "
            "Do NOT discuss technical details or anything outside products/prices/availability. "
            "Never invent items or prices—use exactly what's in the catalog."
        )
        # Build compact catalog text
        try:
            lines = []
            for item in (catalog or []):
                n = str(item.get('name', '')).strip()
                c = str(item.get('category', '')).strip()
                p = item.get('price')
                try:
                    ptxt = f"{float(p):.2f}"
                except Exception:
                    ptxt = str(p)
                if n:
                    lines.append(f"- {n} [{c}] - ${ptxt}")
            catalog_text = "\n".join(lines)
        except Exception:
            catalog_text = ""

        convo = []
        try:
            for turn in (history or [])[-6:]:
                role = turn.get('role', 'user')
                content = (turn.get('content') or '').strip()
                if content:
                    convo.append(f"{role.capitalize()}: {content}")
        except Exception:
            pass
        convo_text = "\n".join(convo)

        prompt = f"""
        {sys_rules}

        Catalog (available items):
        {catalog_text}

        Conversation so far:
        {convo_text}

        User: {question}
        Assistant: """
        fallback = "I can help with available KFC products and prices only. Please ask about items on the menu."
        result = self._safe_generate(prompt, fallback)
        return self._tidy(result, max_chars=700)
