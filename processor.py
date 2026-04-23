import re
import threading
from typing import Optional, Dict, List
import config
import logging
import sys
import os

logger = logging.getLogger(__name__)

class StressProcessor:
    def __init__(self):
        self.accentizer = None
        self._loading = False
        self._ready = threading.Event()
        self._error: Optional[str] = None

    def load_model(self):
        """Загрузка модели с патчингом ONNX в памяти."""
        self._loading = True
        try:
            # Импортируем внутри, так как либа тяжелая
            from ruaccent import RUAccent
            import numpy as np

            # --- MONKEY PATCHING START ---
            # Нам нужно, чтобы ONNX сессия не падала из-за отсутствия token_type_ids
            # Патчим базовый класс модели, если он использует onnxruntime
            try:
                import ruaccent.accent_model
                import ruaccent.omograph_model
                
                def patched_run(self_model, inputs):
                    input_names = [i.name for i in self_model.session.get_inputs()]
                    if 'token_type_ids' in input_names and 'token_type_ids' not in inputs:
                        inputs['token_type_ids'] = np.zeros_like(inputs['input_ids'])
                    return self_model.session.run(None, inputs)

                # Подменяем метод run в обоих классах моделей
                ruaccent.accent_model.AccentModel.run = patched_run
                ruaccent.omograph_model.OmographModel.run = patched_run
                logger.info("RuAccent patched in memory successfully.")
            except Exception as e:
                logger.warning(f"Could not apply memory patch: {e}")
            # --- MONKEY PATCHING END ---

            a = RUAccent()
            a.load(
                omograph_model_size="turbo", 
                use_dictionary=False, 
                custom_dict=config.CUSTOM_DICT,
                custom_homographs=config.CUSTOM_HOMOGRAPHS
            )
            
            # Гарантируем, что "лет" не станет "лёт"
            if hasattr(a, 'yo_words'):
                a.yo_words.pop("лет", None)
                a.yo_words["лет"] = "лет"
                
            self.accentizer = a
            logger.info("Models loaded successfully.")
        except Exception as e:
            self._error = str(e)
            logger.error("Failed to load models", exc_info=True)
        finally:
            self._loading = False
            self._ready.set()

    def start_loading(self):
        threading.Thread(target=self.load_model, daemon=True).start()

    def wait_until_ready(self, timeout: int = 300) -> bool:
        return self._ready.wait(timeout=timeout)

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set() and self.accentizer is not None

    def _convert_plus_to_unicode(self, text: str) -> str:
        """Переводит +а в а́"""
        pattern = r'\+([\u0430\u0435\u0451\u0438\u043e\u0443\u044b\u044d\u044e\u044f\u0410\u0415\u0401\u0418\u041e\u0423\u042b\u042d\u042e\u042f])'
        return re.sub(pattern, r'\1' + config.ACUTE_ACCENT, text)

    def process(self, text: str) -> str:
        if not self.accentizer:
            return text

        processed = self.accentizer.process_all(text)
        visual_text = self._convert_plus_to_unicode(processed)
        return self._final_clean(visual_text)

    def _final_clean(self, text: str) -> str:
        """Твои золотые правила, Шеф. Перенесены без потерь."""
        def word_fix(match: re.Match) -> str:
            word = match.group(0)
            # Чистая версия для проверки
            test = word.replace(config.ACUTE_ACCENT, "").replace("ё", "е").lower()
            
            # 1. Удаление лишних ударений
            if test in config.REMOVAL_LIST:
                res = word.replace(config.ACUTE_ACCENT, "")
                if test == "лет":
                    res = res.replace("ё", "е")
                return res
            
            # 2. Фикс "узнаете"
            if test == "узнаете":
                res = "узна" + config.ACUTE_ACCENT + "ете"
                if word[0].isupper(): 
                    res = res.capitalize()
                return res
            
            return word

        # Ищем последовательности русских букв включая ударения
        pattern = re.compile(r'[а-яА-ЯёЁ' + config.ACUTE_ACCENT + r']+')
        return re.sub(pattern, word_fix, text)
