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
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TOKEN NÃO ENCONTRADO! Configure a variável de ambiente TELEGRAM_TOKEN")
    exit(1)

DB_NAME = "tarefas.db"

# "Estados" da nossa conversa para adicionar tarefas
GET_TITLE, GET_ATTACHMENT = range(2)

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
    """Retorna o teclado principal do bot."""
    keyboard = [
        [KeyboardButton("📝 Ver Minhas Tarefas")],
        [KeyboardButton("➕ Adicionar Nova Tarefa")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# =============================================================================
# COMANDOS PRINCIPAIS (START E CANCELAR)
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função de boas-vindas que apresenta o teclado principal."""
    try:
        user_name = update.effective_user.first_name
        await update.message.reply_text(
            f"Olá, {user_name}! ✨\n\nBem-vindo ao seu assistente de tarefas pessoal. "
            f"Estou aqui para te ajudar a organizar seu dia.",
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Erro no comando start: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual (como adicionar uma tarefa)."""
    try:
        await update.message.reply_text("Operação cancelada.", reply_markup=get_main_keyboard())
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
        await update.message.reply_text("Ótimo! Por favor, me diga o título da sua nova tarefa.")
        return GET_TITLE
    except Exception as e:
        logger.error(f"Erro ao iniciar adição de tarefa: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")
        return ConversationHandler.END

async def get_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o título da tarefa e pergunta sobre anexos."""
    try:
        context.user_data['titulo'] = update.message.text
        keyboard = [
            [InlineKeyboardButton("🖼️ Adicionar Foto/Vídeo", callback_data='add_media')],
            [InlineKeyboardButton("🔗 Adicionar Link", callback_data='add_link')],
            [InlineKeyboardButton("➡️ Pular Anexo", callback_data='skip_attachment')],
        ]
        await update.message.reply_text(
            "Título definido! Deseja adicionar um anexo a esta tarefa?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GET_ATTACHMENT
    except Exception as e:
        logger.error(f"Erro ao receber título da tarefa: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")
        return ConversationHandler.END

async def ask_for_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar a mídia."""
    try:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Ok, agora me envie a foto ou o vídeo.")
        return GET_ATTACHMENT
    except Exception as e:
        logger.error(f"Erro ao solicitar mídia: {e}")
        return GET_ATTACHMENT

async def ask_for_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar o link."""
    try:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Certo, pode me enviar o link (URL completo).")
        return GET_ATTACHMENT
    except Exception as e:
        logger.error(f"Erro ao solicitar link: {e}")
        return GET_ATTACHMENT

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
        if update.message.photo:
            attachment = update.message.photo[-1]
            context.user_data['id_anexo'] = attachment.file_id
            context.user_data['tipo_anexo'] = 'foto'
        elif update.message.video:
            attachment = update.message.video
            context.user_data['id_anexo'] = attachment.file_id
            context.user_data['tipo_anexo'] = 'video'
        else:
            await update.message.reply_text("❌ Tipo de anexo não suportado.")
            return GET_ATTACHMENT

        success = await save_task(update.effective_user.id, context)
        if success:
            await update.message.reply_text("✅ Tarefa e anexo salvos com sucesso!", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("❌ Erro ao salvar tarefa. Tente novamente.", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro ao receber anexo: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um link e salva a tarefa."""
    try:
        link_text = update.message.text
        # Validação básica de URL
        if not (link_text.startswith('http://') or link_text.startswith('https://')):
            await update.message.reply_text("❌ Por favor, envie um link válido (começando com http:// ou https://)")
            return GET_ATTACHMENT
            
        context.user_data['id_anexo'] = link_text
        context.user_data['tipo_anexo'] = 'link'
        
        success = await save_task(update.effective_user.id, context)
        if success:
            await update.message.reply_text("✅ Tarefa e link salvos com sucesso!", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("❌ Erro ao salvar tarefa. Tente novamente.", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro ao receber link: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

async def skip_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pula a etapa do anexo e salva a tarefa."""
    try:
        query = update.callback_query
        await query.answer()
        
        success = await save_task(update.effective_user.id, context)
        if success:
            await query.edit_message_text("✅ Tarefa salva com sucesso!", reply_markup=get_main_keyboard())
        else:
            await query.edit_message_text("❌ Erro ao salvar tarefa. Tente novamente.", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro ao pular anexo: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Ocorreu um erro. Tente novamente mais tarde.")
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
            await update.message.reply_text("Você está em dia! Nenhuma tarefa pendente. ✨", reply_markup=get_main_keyboard())
            return

        await update.message.reply_text("Aqui estão suas tarefas pendentes:")
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
                keyboard.append([InlineKeyboardButton("🔗 Abrir Link", url=tarefa['id_anexo'])])

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Envia o anexo se existir, ou apenas o texto
            try:
                if tarefa['tipo_anexo'] == 'foto':
                    await context.bot.send_photo(chat_id=user_id, photo=tarefa['id_anexo'], caption=tarefa['titulo'], reply_markup=reply_markup)
                elif tarefa['tipo_anexo'] == 'video':
                    await context.bot.send_video(chat_id=user_id, video=tarefa['id_anexo'], caption=tarefa['titulo'], reply_markup=reply_markup)
                else:
                    await context.bot.send_message(chat_id=user_id, text=f"📝 {tarefa['titulo']}", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Erro ao enviar tarefa {task_id}: {e}")
                await context.bot.send_message(chat_id=user_id, text=f"❌ Erro ao carregar tarefa: {tarefa['titulo']}")
                
    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar tarefas do banco de dados: {e}")
        await update.message.reply_text("❌ Erro ao buscar tarefas. Tente novamente mais tarde.", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Erro inesperado ao listar tarefas: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.", reply_markup=get_main_keyboard())

async def handle_task_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa os cliques nos botões 'Concluir' ou 'Apagar'."""
    try:
        query = update.callback_query
        await query.answer()

        action, task_id = query.data.split('_')
        task_id = int(task_id)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if action == "done":
            cursor.execute("UPDATE tarefas SET concluida = 1 WHERE id = ?", (task_id,))
            await query.edit_message_text("Tarefa concluída com sucesso! 👍")
            logger.info(f"Tarefa {task_id} concluída")
        elif action == "delete":
            cursor.execute("DELETE FROM tarefas WHERE id = ?", (task_id,))
            await query.edit_message_text("Tarefa apagada permanentemente. 🗑️")
            logger.info(f"Tarefa {task_id} deletada")
        
        conn.commit()
        conn.close()
    except ValueError:
        logger.error(f"ID de tarefa inválido: {query.data}")
        await query.edit_message_text("❌ Erro: tarefa inválida.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar tarefa no banco de dados: {e}")
        await query.edit_message_text("❌ Erro ao processar tarefa.")
    except Exception as e:
        logger.error(f"Erro inesperado ao processar botão: {e}")
        await query.edit_message_text("❌ Ocorreu um erro.")

# =============================================================================
# COMANDO HELP
# =============================================================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra informações de ajuda sobre o bot."""
    try:
        help_text = """
🤖 *Bot de Tarefas Pessoal*

📝 Comandos disponíveis:
• /start - Iniciar o bot
• /help - Mostrar esta ajuda
• /cancelar - Cancelar operação atual

💡 Como usar:
1. Clique em "➕ Adicionar Nova Tarefa"
2. Digite o título da tarefa
3. Opcionalmente, adicione foto, vídeo ou link
4. Veja suas tarefas em "📝 Ver Minhas Tarefas"
5. Conclua ou apague tarefas usando os botões
        """
        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Erro no comando help: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")

# =============================================================================
# FUNÇÃO PRINCIPAL (INICIALIZADOR PROFISSIONAL)
# =============================================================================
def main() -> None:
    """Função principal que configura e inicia o bot com todas as novas funcionalidades."""
    try:
        logger.info("Iniciando o bot profissional...")
        setup_database()

        if not TELEGRAM_TOKEN:
            logger.error("TOKEN NÃO ENCONTRADO! Configure a variável de ambiente TELEGRAM_TOKEN")
            return

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Handler da conversa para adicionar tarefas
        add_task_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^➕ Adicionar Nova Tarefa$'), start_add_task)],
            states={
                GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_title)],
                GET_ATTACHMENT: [
                    CallbackQueryHandler(ask_for_media, pattern='^add_media$'),
                    CallbackQueryHandler(ask_for_link, pattern='^add_link$'),
                    CallbackQueryHandler(skip_attachment, pattern='^skip_attachment$'),
                    MessageHandler(filters.PHOTO | filters.VIDEO, get_attachment),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_link),
                ],
            },
            fallbacks=[CommandHandler('cancelar', cancel)],
        )

        application.add_handler(add_task_conv_handler)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cancelar", cancel))
        application.add_handler(MessageHandler(filters.Regex('^📝 Ver Minhas Tarefas$'), list_tasks))
        application.add_handler(CallbackQueryHandler(handle_task_button, pattern='^(done|delete)_'))
        
        logger.info("Bot em modo profissional. Aguardando comandos e interações.")
        application.run_polling()
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar o bot: {e}")
        raise

if __name__ == '__main__':
    main()
