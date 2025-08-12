# -*- coding: utf-8 -*-

# =============================================================================
# BIBLIOTECAS (FERRAMENTAS)
# =============================================================================
import sqlite3
import logging
import html
import traceback
import json
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
from telegram.constants import ParseMode

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
# BANCO DE DADOS (Sem alterações)
# =============================================================================
def setup_database():
    """Cria/conecta ao DB e garante que a nova tabela de tarefas exista."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
# INTERFACE E COMANDOS PRINCIPAIS
# =============================================================================
def get_main_keyboard():
    """Retorna o teclado principal do bot."""
    keyboard = [[KeyboardButton("📝 Ver Minhas Tarefas"), KeyboardButton("➕ Adicionar Nova Tarefa")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função de boas-vindas que apresenta o teclado principal."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Olá, {user_name}! ✨\n\nBem-vindo ao seu assistente de tarefas pessoal. "
        f"Estou aqui para te ajudar a organizar seu dia.",
        reply_markup=get_main_keyboard(),
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual e retorna ao menu principal."""
    await update.message.reply_text("Operação cancelada.", reply_markup=get_main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# =============================================================================
# ADICIONAR TAREFA (FLUXO DE CONVERSA MELHORADO)
# =============================================================================
async def start_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de adicionar uma nova tarefa."""
    await update.message.reply_text("Ótimo! Por favor, me diga o título da sua nova tarefa. "
                                    "Ou digite /cancelar para voltar.")
    return GET_TITLE

async def get_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o título e pergunta sobre anexos com botões melhorados."""
    context.user_data['titulo'] = update.message.text
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Foto/Vídeo", callback_data='add_media'),
            InlineKeyboardButton("🔗 Link", callback_data='add_link'),
        ],
        [InlineKeyboardButton("➡️ Pular Anexo", callback_data='skip_attachment')],
    ]
    await update.message.reply_text(
        "Título definido! Deseja adicionar um anexo a esta tarefa?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GET_ATTACHMENT

async def back_to_attachment_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função para o botão 'Voltar', retorna à seleção de tipo de anexo."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Foto/Vídeo", callback_data='add_media'),
            InlineKeyboardButton("🔗 Link", callback_data='add_link'),
        ],
        [InlineKeyboardButton("➡️ Pular Anexo", callback_data='skip_attachment')],
    ]
    await query.edit_message_text(
        "Sem problemas. Escolha uma opção de anexo ou pule esta etapa.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GET_ATTACHMENT

async def ask_for_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar a mídia, com opção de voltar."""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='back_to_options')]]
    await query.edit_message_text("Ok, agora me envie a foto ou o vídeo.", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ATTACHMENT

async def ask_for_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar o link, com opção de voltar."""
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='back_to_options')]]
    await query.edit_message_text("Certo, pode me enviar o link (URL completo).", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ATTACHMENT

async def save_task_and_reply(update, context: ContextTypes.DEFAULT_TYPE, confirmation_text: str):
    """Função centralizada para salvar a tarefa e enviar confirmação."""
    user_id = update.effective_user.id
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
    
    context.user_data.clear()
    
    # Envia uma nova mensagem de confirmação com o teclado principal
    await context.bot.send_message(
        chat_id=user_id,
        text=confirmation_text,
        reply_markup=get_main_keyboard()
    )

async def get_attachment_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um anexo (foto ou vídeo) e salva a tarefa."""
    attachment = update.message.photo[-1] if update.message.photo else update.message.video
    context.user_data['id_anexo'] = attachment.file_id
    context.user_data['tipo_anexo'] = 'foto' if update.message.photo else 'video'
    
    await save_task_and_reply(update, context, "✅ Tarefa e anexo salvos com sucesso!")
    return ConversationHandler.END

async def get_link_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um link e salva a tarefa."""
    context.user_data['id_anexo'] = update.message.text
    context.user_data['tipo_anexo'] = 'link'
    
    await save_task_and_reply(update, context, "✅ Tarefa e link salvos com sucesso!")
    return ConversationHandler.END

async def skip_attachment_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pula a etapa do anexo e salva a tarefa. CORRIGIDO."""
    query = update.callback_query
    await query.answer()
    await query.delete_message() # Deleta a mensagem com os botões para limpar o chat
    
    await save_task_and_reply(update, context, "✅ Tarefa salva com sucesso!")
    return ConversationHandler.END

# =============================================================================
# VER E GERENCIAR TAREFAS (Sem alterações)
# =============================================================================
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Esta função continua a mesma da versão anterior, já era bem robusta.
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
        if tarefa['tipo_anexo'] == 'link':
            keyboard.append([InlineKeyboardButton("🔗 Abrir Link", url=tarefa['id_anexo'])])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if tarefa['tipo_anexo'] == 'foto':
            await context.bot.send_photo(chat_id=user_id, photo=tarefa['id_anexo'], caption=f"📝 {tarefa['titulo']}", reply_markup=reply_markup)
        elif tarefa['tipo_anexo'] == 'video':
            await context.bot.send_video(chat_id=user_id, video=tarefa['id_anexo'], caption=f"📝 {tarefa['titulo']}", reply_markup=reply_markup)
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
# GESTOR DE ERROS (NOVO E ESSENCIAL)
# =============================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loga os erros causados por updates."""
    logging.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Limita o tamanho da mensagem de erro para não exceder o limite do Telegram
    error_message = (
        f"Ocorreu um erro no bot:\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    # Tenta notificar o desenvolvedor (ou o usuário) sobre o erro.
    if update and hasattr(update, 'effective_chat'):
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text="Opa, ocorreu um erro interno. Já estou verificando!", parse_mode=ParseMode.HTML)


# =============================================================================
# FUNÇÃO PRINCIPAL (INICIALIZADOR)
# =============================================================================
def main() -> None:
    """Função principal que configura e inicia o bot com todas as novas funcionalidades."""
    logging.info("Iniciando o bot profissional...")
    setup_database()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Adiciona o gestor de erros
    application.add_error_handler(error_handler)

    # Handler da conversa para adicionar tarefas (agora com opção de voltar)
    add_task_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ Adicionar Nova Tarefa$'), start_add_task)],
        states={
            GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_title)],
            GET_ATTACHMENT: [
                CallbackQueryHandler(ask_for_media, pattern='^add_media$'),
                CallbackQueryHandler(ask_for_link, pattern='^add_link$'),
                CallbackQueryHandler(skip_attachment_and_save, pattern='^skip_attachment$'),
                CallbackQueryHandler(back_to_attachment_options, pattern='^back_to_options$'), # Opção de voltar
                MessageHandler(filters.PHOTO | filters.VIDEO, get_attachment_and_save),
                MessageHandler(filters.Regex(r'^(https|http)://'), get_link_and_save),
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

