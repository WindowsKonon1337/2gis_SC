# Transportation Analysis System

Система анализа городского транспорта с использованием микросервисной архитектуры.

## Архитектура

Проект состоит из трех основных сервисов:

- **LLM Service** (порт 1337) - сервис для работы с языковыми моделями
- **Crowd Analysis Service** (порт 1338) - сервис анализа толпы

## Быстрый старт

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd template
```

### 2. Запуск с Docker Compose
```bash
# Запуск всех сервисов
docker-compose up --build -d
```

```bash
# Просмотр логов
docker-compose logs -f
```

```bash
# Остановка сервисов
docker-compose down
```

### Для проверки проекта после запуска compose файла необходимо открыть [html-файл](./prototype.html) и дальше наслаждаться функционалом. Пример данных находится в папке [data](./data/)

### 3. Переменные окружения

В docker compose необходимо указать ссылку на провайдера и ключ API

```docker-compose
      - OPENAI_API_KEY=${OPENAI_API_KEY:-<YOUR KEY HERE>}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL:-<OPENROUTER || PROXYAPI>}
```

## API Endpoints

После запуска сервисы будут доступны по следующим адресам:

- **LLM Service**: http://localhost:1337
- **Crowd Analysis Service**: http://localhost:1338

## Разработка


### Пересборка образов

```bash
# Пересборка всех образов
docker-compose build

# Пересборка конкретного сервиса
docker-compose build llm-service
```

### Просмотр состояния

```bash
# Статус контейнеров
docker-compose ps

# Логи конкретного сервиса
docker-compose logs llm-service

# Подключение к контейнеру
docker-compose exec llm-service sh
```

## Структура проекта

```
template/
├── docker-compose.yaml          # Конфигурация Docker Compose
├── data/                        # Статические файлы данных
├── src/services/
│   ├── llm_service/            # LLM сервис
│   ├── crowd_analysis_service/ # Сервис анализа толпы
└── README.md                   # Документация
```

## Troubleshooting

### Проверка здоровья сервисов
```bash
# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs

# Перезапуск сервиса
docker-compose restart llm-service
```

### Очистка
```bash
# Остановка и удаление контейнеров
docker-compose down

# Удаление с очисткой volumes
docker-compose down -v

# Удаление образов
docker-compose down --rmi all
```
