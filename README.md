# Transportation Analysis System

Система анализа городского транспорта с использованием микросервисной архитектуры.

## Архитектура

Проект состоит из трех основных сервисов:

- **LLM Service** (порт 1337) - сервис для работы с языковыми моделями
- **Crowd Analysis Service** (порт 1338) - сервис анализа толпы
- **Gateway Service** (порт 1339) - шлюз для маршрутизации запросов
- **Nginx** (порт 80) - обратный прокси для объединения сервисов

## Быстрый старт

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd template
```

### 2. Запуск с Docker Compose
```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down
```

### 3. Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# LLM Service Configuration
LLM_SERVICE_PORT=1337
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1

# Crowd Analysis Service Configuration
CROWD_ANALYSIS_SERVICE_PORT=1338

# Gateway Service Configuration
GATEWAY_SERVICE_PORT=1339

# Nginx Configuration
NGINX_PORT=80
NGINX_SSL_PORT=443
```

## API Endpoints

После запуска сервисы будут доступны по следующим адресам:

- **LLM Service**: http://localhost:1337
- **Crowd Analysis Service**: http://localhost:1338
- **Gateway Service**: http://localhost:1339
- **Nginx Proxy**: http://localhost (объединяет все сервисы)

### Через Nginx:
- LLM API: http://localhost/api/v1/llm/
- Crowd Analysis API: http://localhost/api/v1/crowd/
- Gateway API: http://localhost/api/v1/gateway/

## Разработка

### Запуск отдельных сервисов

```bash
# Только LLM сервис
docker-compose up llm-service

# Только Crowd Analysis сервис
docker-compose up crowd-analysis-service

# Только Gateway сервис
docker-compose up gateway-service
```

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
├── nginx.conf                   # Конфигурация Nginx
├── data/                        # Статические файлы данных
├── src/services/
│   ├── llm_service/            # LLM сервис
│   ├── crowd_analysis_service/ # Сервис анализа толпы
│   └── gateaway/               # Gateway сервис
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
