# -*- coding: utf-8 -*-

# =============================================================================
# BIBLIOTECAS (FERRAMENTAS)
# =============================================================================
import sqlite3
import logging
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

# Seu token do Telegram.
TELEGRAM_TOKEN = "8272131356:AAGi_CDSPoFDCEq53WhPorWH1NG5nKdAayA"
DB_NAME = "tarefas.db"

# "Estados" da nossa conversa para adicionar tarefas
GET_TITLE, GET_ATTACHMENT = range(2)

# =============================================================================
# BANCO DE DADOS (AGORA MAIS PODEROSO)
# =============================================================================
def setup_database():
    """Cria/conecta ao DB e garante que a nova tabela de tarefas exista."""
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
    logging.info(f"Banco de dados profissional '{DB_NAME}' pronto.")

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
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Olá, {user_name}! ✨\n\nBem-vindo ao seu assistente de tarefas pessoal. "
        f"Estou aqui para te ajudar a organizar seu dia.",
        reply_markup=get_main_keyboard(),
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual (como adicionar uma tarefa)."""
    await update.message.reply_text("Operação cancelada.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# =============================================================================
# FUNCIONALIDADE: ADICIONAR TAREFA (CONVERSATION HANDLER)
# =============================================================================
async def start_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de adicionar uma nova tarefa."""
    await update.message.reply_text("Ótimo! Por favor, me diga o título da sua nova tarefa.")
    return GET_TITLE

async def get_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o título da tarefa e pergunta sobre anexos."""
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

async def ask_for_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar a mídia."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ok, agora me envie a foto ou o vídeo.")
    return GET_ATTACHMENT

async def ask_for_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar o link."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Certo, pode me enviar o link (URL completo).")
    return GET_ATTACHMENT

async def save_task(user_id, context):
    """Função auxiliar para salvar a tarefa no banco de dados."""
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

async def get_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um anexo (foto ou vídeo) e salva a tarefa."""
    attachment = update.message.photo[-1] if update.message.photo else update.message.video
    context.user_data['id_anexo'] = attachment.file_id
    context.user_data['tipo_anexo'] = 'foto' if update.message.photo else 'video'
    
    await save_task(update.effective_user.id, context)
    await update.message.reply_text("✅ Tarefa e anexo salvos com sucesso!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um link e salva a tarefa."""
    context.user_data['id_anexo'] = update.message.text
    context.user_data['tipo_anexo'] = 'link'
    
    await save_task(update.effective_user.id, context)
    await update.message.reply_text("✅ Tarefa e link salvos com sucesso!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def skip_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pula a etapa do anexo e salva a tarefa."""
    query = update.callback_query
    await query.answer()
    
    await save_task(update.effective_user.id, context)
    await query.edit_message_text("✅ Tarefa salva com sucesso!", reply_markup=get_main_keyboard())
    return ConversationHandler.END
    
# =============================================================================
# FUNCIONALIDADE: VER E GERENCIAR TAREFAS
# =============================================================================
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca as tarefas no DB e as envia uma por uma com botões."""
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, tipo_anexo, id_anexo FROM tarefas WHERE user_id = ? AND concluida = 0", (user_id,))
    tarefas = cursor.fetchall()
    conn.close()

    if not tarefas:
        await update.message.reply_text("Você está em dia! Nenhuma tarefa pendente. ✨")
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
        if tarefa['tipo_anexo'] == 'foto':
            await context.bot.send_photo(chat_id=user_id, photo=tarefa['id_anexo'], caption=tarefa['titulo'], reply_markup=reply_markup)
        elif tarefa['tipo_anexo'] == 'video':
            await context.bot.send_video(chat_id=user_id, video=tarefa['id_anexo'], caption=tarefa['titulo'], reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=user_id, text=f"📝 {tarefa['titulo']}", reply_markup=reply_markup)

async def handle_task_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa os cliques nos botões 'Concluir' ou 'Apagar'."""
    query = update.callback_query
    await query.answer()

    action, task_id = query.data.split('_')
    task_id = int(task_id)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if action == "done":
        cursor.execute("UPDATE tarefas SET concluida = 1 WHERE id = ?", (task_id,))
        await query.edit_message_text("Tarefa concluída com sucesso! 👍")
    elif action == "delete":
        cursor.execute("DELETE FROM tarefas WHERE id = ?", (task_id,))
        await query.edit_message_text("Tarefa apagada permanentemente. 🗑️")
    
    conn.commit()
    conn.close()

# =============================================================================
# FUNÇÃO PRINCIPAL (INICIALIZADOR PROFISSIONAL)
# =============================================================================
def main() -> None:
    """Função principal que configura e inicia o bot com todas as novas funcionalidades."""
    logging.info("Iniciando o bot profissional...")
    setup_database()

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
    application.add_handler(CommandHandler("cancelar", cancel))
    application.add_handler(MessageHandler(filters.Regex('^📝 Ver Minhas Tarefas$'), list_tasks))
    application.add_handler(CallbackQueryHandler(handle_task_button, pattern='^(done|delete)_'))
    
    logging.info("Bot em modo profissional. Aguardando comandos e interações.")
    application.run_polling()

if __name__ == '__main__':
    main()

