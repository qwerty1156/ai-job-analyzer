"""
Настройка логирования.

Формат: время | уровень | логгер | сообщение — этого достаточно, чтобы
читать логи в docker compose logs / journald без доп. тулинга.

ВАЖНО: нигде в логах не должно быть секретов — API-ключей (AI_API_KEY),
паролей, JWT-токенов, JWT_SECRET, строки подключения к БД с паролем.
Правила, которых мы придерживаемся по всему проекту:
    - логируем метаданные запроса (метод, путь, статус, длительность,
      id пользователя), НИКОГДА не логируем тело запроса целиком
      (там может быть password при /register и /login);
    - логируем длины/факты про AI-запрос (провайдер, модель, кол-во
      навыков), а не сам текст вакансии/резюме и уж тем более не ключ;
    - при логировании ошибок используем exc.message/str(exc) от наших
      же доменных исключений, а не сырые объекты настроек.
"""

import logging


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Библиотеки, которые излишне многословны на INFO — приглушаем.
    for noisy_logger in ("httpx", "httpcore", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
