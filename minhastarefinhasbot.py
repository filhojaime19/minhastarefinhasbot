# -*- coding: utf-8 -*-

# =============================================================================
# BIBLIOTECAS (FERRAMENTAS)
# =============================================================================
import sqlite3
import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =============================================================================
# CONFIGURAÇÃO E CONSTANTES
# =============================================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🚨 TOKEN AGORA VEM DE VARIÁVEL DE AMBIENTE 🚨
# Substituindo o método de obtenção do token para uso direto.
TELEGRAM_TOKEN = "8272131356:AAGi_CDSPoFDCEq53WhPorWH1NG5nKdAayA"  # INSIRA SEU TOKEN AQUI DIRETAMENTE

if not TELEGRAM_TOKEN:
    logger.error("TOKEN NÃO ENCONTRADO! Configure a variável de ambiente TELEGRAM_TOKEN")
    exit(1)

DB_NAME = "tarefas.db"

# "Estados" da nossa conversa para adicionar tarefas
GET_TITLE, GET_ATTACHMENT, GET_LINK = range(3)

# =============================================================================
# BANCO DE DADOS (AGORA MAIS PODEROSO E SEGURO)
# =============================================================================
def setup_database():
    """Cria/conecta ao DB e garante que a nova tabela de tarefas exista."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # ATUALIZAÇÃO: Nova tabela com colunas para anexos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                tipo_anexo TEXT DEFAULT 'nenhum',
                id_anexo TEXT,
                concluida INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"Banco de dados profissional '{DB_NAME}' pronto.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao configurar banco de dados: {e}")
        raise

# =============================================================================
# FUNÇÕES DE INTERFACE (TECLADOS E BOTÕES)
# =============================================================================
def get_main_keyboard():
    """Retorna o teclado principal do bot com layout profissional."""
    keyboard = [
        [
            KeyboardButton("➕ Nova Tarefa"), 
            KeyboardButton("📝 Minhas Tarefas")
        ],
        [
            KeyboardButton("❓ Sobre")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_attachment_keyboard():
    """Retorna o teclado para escolher tipo de anexo."""
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Foto", callback_data='add_media'),
            InlineKeyboardButton("🔗 Link", callback_data='add_link')
        ],
        [
            InlineKeyboardButton("⏭️ Pular", callback_data='skip_attachment')
        ],
        [
            InlineKeyboardButton("🔙 Voltar", callback_data='back_to_title')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    """Retorna o teclado com opção de cancelar."""
    keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data='cancel_operation')]]
    return InlineKeyboardMarkup(keyboard)

# =============================================================================
# COMANDOS PRINCIPAIS (START E CANCELAR)
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função de boas-vindas que apresenta o teclado principal."""
    try:
        user_name = update.effective_user.first_name
        welcome_message = f"""🌟 Olá, {user_name}!

Bem-vindo ao seu Assistente de Tarefas Pessoal!

Organize sua vida de forma simples e eficiente. Crie tarefas, adicione anexos e acompanhe seu progresso.

Selecione uma opção abaixo para começar:"""
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Erro no comando start: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra informações sobre o bot."""
    try:
        about_text = """🤖 *Sobre o Bot de Tarefas*

📝 *Proposta:*
Este bot foi criado para ajudar você a organizar suas tarefas diárias de forma simples e eficiente. Com ele, você pode:
• Criar e gerenciar tarefas pessoais
• Adicionar anexos (fotos, vídeos, links)
• Marcar tarefas como concluídas
• Manter tudo organizado em um só lugar

✨ *Diferenciais:*
• Interface intuitiva e profissional
• Suporte para anexos diversos
• Sincronização em tempo real
• Totalmente gratuito e privado

Desenvolvido com ❤️ para facilitar sua vida!"""
        
        await update.message.reply_text(
            about_text, 
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Erro no comando about: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual (como adicionar uma tarefa)."""
    try:
        await update.message.reply_text(
            "❌ Operação cancelada.", 
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro no comando cancel: {e}")
        return ConversationHandler.END

# Continua o código para outras funcionalidades, conforme descrito acima...
