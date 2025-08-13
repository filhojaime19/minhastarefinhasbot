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

# 🚨 TOKEN EMBUTIDO (APENAS PARA TESTE - NÃO USAR EM PRODUÇÃO) 🚨
TELEGRAM_TOKEN = "8272131356:AAGi_CDSPoFDCEq53WhPorWH1NG5nKdAayA"

DB_NAME = "tarefas.db"

# "Estados" da nossa conversa para adicionar tarefas
GET_TITLE, GET_ATTACHMENT, GET_LINK = range(3)

# =============================================================================
# BANCO DE DADOS (AGORA MAIS PODEROSO E SEGURO)
# =============================================================================
def setup_database():
    """Cria/conecta ao DB e garante que a nova tabela de tarefas exista."""
    try:
        logger.info("Tentando criar/conectar ao banco de dados...")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        logger.info("Conexão com banco estabelecida com sucesso")
        
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
        logger.error(f"Erro SQLite ao configurar banco de dados: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro geral ao configurar banco de dados: {e}")
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
        # Limpa os dados da conversa
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro no comando cancel: {e}")
        return ConversationHandler.END

# =============================================================================
# FUNCIONALIDADE: ADICIONAR TAREFA (CONVERSATION HANDLER)
# =============================================================================
async def start_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de adicionar uma nova tarefa."""
    try:
        await update.message.reply_text(
            "📝 *Nova Tarefa*\n\nPor favor, me diga o título da sua nova tarefa:",
            parse_mode='Markdown',
            reply_markup=get_cancel_keyboard()
        )
        return GET_TITLE
    except Exception as e:
        logger.error(f"Erro ao iniciar adição de tarefa: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")
        return ConversationHandler.END

async def get_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o título da tarefa e pergunta sobre anexos."""
    try:
        # Verifica se o usuário quer cancelar
        if update.message.text.startswith('/cancelar'):
            await update.message.reply_text(
                "❌ Operação cancelada.", 
                reply_markup=get_main_keyboard()
            )
            # Limpa os dados da conversa
            context.user_data.clear()
            return ConversationHandler.END
            
        context.user_data['titulo'] = update.message.text
        await update.message.reply_text(
            f"✅ Título definido: *{update.message.text}*\n\nDeseja adicionar um anexo a esta tarefa?",
            parse_mode='Markdown',
            reply_markup=get_attachment_keyboard()
        )
        return GET_ATTACHMENT
    except Exception as e:
        logger.error(f"Erro ao receber título da tarefa: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")
        return ConversationHandler.END

async def handle_attachment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a escolha do tipo de anexo."""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'add_media':
            await query.edit_message_text(
                "📸 *Adicionar Foto/Vídeo*\n\nAgora me envie a foto ou o vídeo.\n\n"
                "👉 *Dica:* Você pode tirar uma foto direto do Telegram!\n\n"
                " OU envie /cancelar para cancelar a operação.",
                parse_mode='Markdown',
                reply_markup=get_cancel_keyboard()
            )
            return GET_ATTACHMENT
            
        elif query.data == 'add_link':
            await query.edit_message_text(
                "🔗 *Adicionar Link*\n\nPor favor, envie o link completo (começando com http:// ou https://)\n\n"
                " OU envie /cancelar para cancelar a operação.",
                parse_mode='Markdown',
                reply_markup=get_cancel_keyboard()
            )
            return GET_LINK
            
        elif query.data == 'skip_attachment':
            success = await save_task(update.effective_user.id, context)
            if success:
                await query.edit_message_text(
                    "✅ *Tarefa salva com sucesso!*\n\nSua tarefa foi adicionada à lista.",
                    parse_mode='Markdown',
                    reply_markup=None
                )
                # Mostra o menu principal após um pequeno delay
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="📋 *Menu Principal*",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )
            else:
                await query.edit_message_text(
                    "❌ Erro ao salvar tarefa. Tente novamente.",
                    reply_markup=get_main_keyboard()
                )
            return ConversationHandler.END
            
        elif query.data == 'back_to_title':
            await query.edit_message_text(
                "📝 *Nova Tarefa*\n\nPor favor, me diga o título da sua nova tarefa:",
                parse_mode='Markdown',
                reply_markup=get_cancel_keyboard()
            )
            # Limpa os dados anteriores
            context.user_data.clear()
            return GET_TITLE
            
        elif query.data == 'cancel_operation':
            await query.edit_message_text("❌ Operação cancelada.")
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="📋 *Menu Principal*",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            # Limpa os dados da conversa
            context.user_data.clear()
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Erro ao processar escolha de anexo: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Ocorreu um erro.")
        return ConversationHandler.END

async def save_task(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Função auxiliar para salvar a tarefa no banco de dados."""
    try:
        titulo = context.user_data.get('titulo')
        tipo_anexo = context.user_data.get('tipo_anexo', 'nenhum')
        id_anexo = context.user_data.get('id_anexo')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tarefas (user_id, titulo, tipo_anexo, id_anexo) VALUES (?, ?, ?, ?)",
            (user_id, titulo, tipo_anexo, id_anexo)
        )
        conn.commit()
        conn.close()
        
        # Limpa os dados da conversa
        context.user_data.clear()
        logger.info(f"Tarefa salva com sucesso para o usuário {user_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erro ao salvar tarefa no banco de dados: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao salvar tarefa: {e}")
        return False

async def get_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um anexo (foto ou vídeo) e salva a tarefa."""
    try:
        # Verifica se o usuário quer cancelar
        if update.message.text.startswith('/cancelar'):
            await update.message.reply_text(
                "❌ Operação cancelada.", 
                reply_markup=get_main_keyboard()
            )
            # Limpa os dados da conversa
            context.user_data.clear()
            return ConversationHandler.END
            
        if update.message.photo:
            attachment = update.message.photo[-1]
            context.user_data['id_anexo'] = attachment.file_id
            context.user_data['tipo_anexo'] = 'foto'
        elif update.message.video:
            attachment = update.message.video
            context.user_data['id_anexo'] = attachment.file_id
            context.user_data['tipo_anexo'] = 'video'
        else:
            await update.message.reply_text(
                "❌ Tipo de anexo não suportado.\n\nPor favor, envie uma foto ou vídeo.\n\n"
                " OU envie /cancelar para cancelar a operação.",
                reply_markup=get_cancel_keyboard()
            )
            return GET_ATTACHMENT

        success = await save_task(update.effective_user.id, context)
        if success:
            await update.message.reply_text(
                "✅ *Tarefa e anexo salvos com sucesso!*\n\nSua tarefa foi adicionada à lista.",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Erro ao salvar tarefa. Tente novamente.",
                reply_markup=get_main_keyboard()
            )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro ao receber anexo: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro. Tente novamente mais tarde.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um link e salva a tarefa."""
    try:
        # Verifica se o usuário quer cancelar
        if update.message.text.startswith('/cancelar'):
            await update.message.reply_text(
                "❌ Operação cancelada.", 
                reply_markup=get_main_keyboard()
            )
            # Limpa os dados da conversa
            context.user_data.clear()
            return ConversationHandler.END
            
        link_text = update.message.text
        
        # Validação básica de URL
        if not (link_text.startswith('http://') or link_text.startswith('https://')):
            await update.message.reply_text(
                "❌ Por favor, envie um link válido (começando com http:// ou https://)\n\n"
                " OU envie /cancelar para cancelar a operação.",
                reply_markup=get_cancel_keyboard()
            )
            return GET_LINK
            
        context.user_data['id_anexo'] = link_text
        context.user_data['tipo_anexo'] = 'link'
        
        success = await save_task(update.effective_user.id, context)
        if success:
            await update.message.reply_text(
                "✅ *Tarefa e link salvos com sucesso!*\n\nSua tarefa foi adicionada à lista.",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Erro ao salvar tarefa. Tente novamente.",
                reply_markup=get_main_keyboard()
            )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro ao receber link: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro. Tente novamente mais tarde.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

# =============================================================================
# FUNCIONALIDADE: VER E GERENCIAR TAREFAS
# =============================================================================
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca as tarefas no DB e as envia uma por uma com botões."""
    try:
        user_id = update.effective_user.id
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo, tipo_anexo, id_anexo FROM tarefas WHERE user_id = ? AND concluida = 0", (user_id,))
        tarefas = cursor.fetchall()
        conn.close()

        if not tarefas:
            await update.message.reply_text(
                "🎉 *Parabéns!*\n\nVocê está em dia! Nenhuma tarefa pendente.\n\nContinue assim! ✨",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            return

        await update.message.reply_text(
            "📋 *Suas Tarefas Pendentes*\n\nAqui estão as tarefas que você precisa completar:",
            parse_mode='Markdown'
        )
        
        for tarefa in tarefas:
            task_id = tarefa['id']
            keyboard = [
                [
                    InlineKeyboardButton("✅ Concluir", callback_data=f"done_{task_id}"),
                    InlineKeyboardButton("🗑️ Apagar", callback_data=f"delete_{task_id}"),
                ]
            ]
            # Se houver um link, adiciona um botão para ele
            if tarefa['tipo_anexo'] == 'link':
                keyboard.insert(0, [InlineKeyboardButton("🔗 Abrir Link", url=tarefa['id_anexo'])])

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Envia o anexo se existir, ou apenas o texto
            try:
                if tarefa['tipo_anexo'] == 'foto':
                    await context.bot.send_photo(
                        chat_id=user_id, 
                        photo=tarefa['id_anexo'], 
                        caption=f"📝 *{tarefa['titulo']}*",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                elif tarefa['tipo_anexo'] == 'video':
                    await context.bot.send_video(
                        chat_id=user_id, 
                        video=tarefa['id_anexo'], 
                        caption=f"📝 *{tarefa['titulo']}*",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text=f"📝 *{tarefa['titulo']}*",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Erro ao enviar tarefa {task_id}: {e}")
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=f"❌ Erro ao carregar tarefa: *{tarefa['titulo']}*",
                    parse_mode='Markdown'
                )
                
    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar tarefas do banco de dados: {e}")
        await update.message.reply_text(
            "❌ Erro ao buscar tarefas. Tente novamente mais tarde.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao listar tarefas: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro. Te
