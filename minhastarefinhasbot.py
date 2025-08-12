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
# BANCO DE DADOS (ESTRUTURA FINAL)
# =============================================================================
def setup_database():
    """Cria/conecta ao DB e garante que a tabela de tarefas exista."""
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
# FUNÇÕES DE INTERFACE (TECLADOS E BOTÕES)
# =============================================================================
def get_main_keyboard():
    """Retorna o teclado principal do bot com a nova ordem e botão Sobre."""
    keyboard = [
        # MUDANÇA: Ordem dos botões invertida
        [KeyboardButton("➕ Adicionar Nova Tarefa"), KeyboardButton("📝 Ver Minhas Tarefas")],
        # MUDANÇA: Novo botão "Sobre"
        [KeyboardButton("ℹ️ Sobre")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# =============================================================================
# COMANDOS PRINCIPAIS (START, SOBRE E CANCELAR)
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função de boas-vindas que apresenta o teclado principal."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Olá, {user_name}! ✨\n\nBem-vindo ao seu assistente de tarefas pessoal. "
        f"Estou aqui para te ajudar a organizar seu dia.",
        reply_markup=get_main_keyboard(),
    )

# MUDANÇA: Nova função para o botão "Sobre"
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem explicando o que o bot faz."""
    await update.message.reply_text(
        "ℹ️ *Sobre o MinhasTarefinhasBot*\n\n"
        "Eu sou um bot criado para ser seu assistente pessoal de tarefas. "
        "Meu objetivo é tornar o gerenciamento do seu dia a dia mais simples e visual.\n\n"
        "Comigo, você pode:\n"
        "• Adicionar tarefas rapidamente.\n"
        "• Anexar fotos, vídeos ou links às suas tarefas.\n"
        "• Visualizar tudo o que precisa ser feito de forma organizada.\n"
        "• Marcar tarefas como concluídas ou apagá-las com um único clique.\n\n"
        "Sinta-se à vontade para me usar como seu segundo cérebro!",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(),
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual (chamado via comando /cancelar ou botão)."""
    # Verifica se a chamada veio de um botão
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operação cancelada.")
    else:
        await update.message.reply_text("Operação cancelada.", reply_markup=get_main_keyboard())
    
    context.user_data.clear()
    return ConversationHandler.END

# =============================================================================
# FUNCIONALIDADE: ADICIONAR TAREFA (CONVERSATION HANDLER)
# =============================================================================
async def start_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de adicionar uma nova tarefa."""
    await update.message.reply_text(
        "Ótimo! Por favor, me diga o título da sua nova tarefa.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data='cancel')]])
    )
    return GET_TITLE

# MUDANÇA: Agora o teclado de anexo é gerado por uma função separada
def get_attachment_keyboard():
    """Retorna o teclado de opções de anexo."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Adicionar Foto/Vídeo", callback_data='add_media')],
        [InlineKeyboardButton("🔗 Adicionar Link", callback_data='add_link')],
        [InlineKeyboardButton("➡️ Pular Anexo", callback_data='skip_attachment')],
    ])

async def get_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o título da tarefa e pergunta sobre anexos."""
    context.user_data['titulo'] = update.message.text
    # MUDANÇA: A mensagem de "cancelar" é removida e o novo teclado é mostrado
    await update.message.edit_reply_markup(reply_markup=None) 
    await update.message.reply_text(
        "Título definido! Deseja adicionar um anexo a esta tarefa?",
        reply_markup=get_attachment_keyboard()
    )
    return GET_ATTACHMENT

# MUDANÇA: Nova função para o botão "Voltar"
async def back_to_attachment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Volta para a tela de escolha de tipo de anexo."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Sem problemas. Deseja adicionar um tipo diferente de anexo?",
        reply_markup=get_attachment_keyboard()
    )
    return GET_ATTACHMENT

# MUDANÇA: Função de pedir mídia agora inclui botões de Voltar e Cancelar
def get_back_and_cancel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Voltar", callback_data='back_to_attachment_choice'),
            InlineKeyboardButton("❌ Cancelar", callback_data='cancel')
        ]
    ])

async def ask_for_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar a mídia, com novas opções."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Ok, agora me envie a foto ou o vídeo.",
        reply_markup=get_back_and_cancel_keyboard()
    )
    return GET_ATTACHMENT

async def ask_for_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Instrui o usuário a enviar o link, com novas opções."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Certo, pode me enviar o link (URL completo).",
        reply_markup=get_back_and_cancel_keyboard()
    )
    return GET_ATTACHMENT

async def save_task(user_id, context, update_source):
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
    
    context.user_data.clear()
    
    success_message = f"✅ Tarefa '{titulo}' salva com sucesso!"
    
    # Edita a mensagem se veio de um botão, ou responde se veio de um anexo
    if isinstance(update_source, Update) and update_source.callback_query:
        await update_source.callback_query.edit_message_text(success_message)
    else:
        await update_source.message.reply_text(success_message, reply_markup=get_main_keyboard())


async def get_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um anexo (foto ou vídeo) e salva a tarefa."""
    attachment = update.message.photo[-1] if update.message.photo else update.message.video
    context.user_data['id_anexo'] = attachment.file_id
    context.user_data['tipo_anexo'] = 'foto' if update.message.photo else 'video'
    
    await save_task(update.effective_user.id, context, update)
    return ConversationHandler.END

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe um link e salva a tarefa."""
    context.user_data['id_anexo'] = update.message.text
    context.user_data['tipo_anexo'] = 'link'
    
    await save_task(update.effective_user.id, context, update)
    return ConversationHandler.END

async def skip_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pula a etapa do anexo e salva a tarefa."""
    await save_task(update.effective_user.id, context, update)
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
    cursor.execute("SELECT id, titulo, tipo_anexo, id_anexo FROM tarefas WHERE user_id = ? AND concluida = 0 ORDER BY id DESC", (user_id,))
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

        caption = f"📝 *{tarefa['titulo']}*"
        if tarefa['tipo_anexo'] == 'foto':
            await context.bot.send_photo(chat_id=user_id, photo=tarefa['id_anexo'], caption=caption, reply_markup=reply_markup, parse_mode='Markdown')
        elif tarefa['tipo_anexo'] == 'video':
            await context.bot.send_video(chat_id=user_id, video=tarefa['id_anexo'], caption=caption, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_task_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa os cliques nos botões 'Concluir' ou 'Apagar'."""
    query = update.callback_query
    await query.answer()

    action, task_id_str = query.data.split('_', 1)
    task_id = int(task_id_str)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    original_caption = query.message.caption or query.message.text
    
    if action == "done":
        cursor.execute("UPDATE tarefas SET concluida = 1 WHERE id = ?", (task_id,))
        await query.edit_message_text(f"✅ ~~__{original_caption}__~~\n\n*Tarefa concluída com sucesso!*", parse_mode='Markdown')
    elif action == "delete":
        cursor.execute("DELETE FROM tarefas WHERE id = ?", (task_id,))
        await query.edit_message_text(f"🗑️ ~~__{original_caption}__~~\n\n*Tarefa apagada permanentemente.*", parse_mode='Markdown')
    
    conn.commit()
    conn.close()

# =============================================================================
# FUNÇÃO PRINCIPAL (INICIALIZADOR FINAL)
# =============================================================================
def main() -> None:
    """Função principal que configura e inicia o bot com todas as funcionalidades."""
    logging.info("Iniciando a versão final do bot...")
    setup_database()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # MUDANÇA: Lógica de adicionar tarefa agora é mais complexa e robusta
    add_task_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ Adicionar Nova Tarefa$'), start_add_task)],
        states={
            GET_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_title),
                CallbackQueryHandler(cancel, pattern='^cancel$'),
            ],
            GET_ATTACHMENT: [
                CallbackQueryHandler(ask_for_media, pattern='^add_media$'),
                CallbackQueryHandler(ask_for_link, pattern='^add_link$'),
                CallbackQueryHandler(skip_attachment, pattern='^skip_attachment$'),
                CallbackQueryHandler(back_to_attachment_choice, pattern='^back_to_attachment_choice$'),
                CallbackQueryHandler(cancel, pattern='^cancel$'),
                MessageHandler(filters.PHOTO | filters.VIDEO, get_attachment),
                MessageHandler(filters.Entity("url") | filters.Entity("text_link"), get_link),
            ],
        },
        fallbacks=[CommandHandler('cancelar', cancel)],
        per_message=False
    )

    application.add_handler(add_task_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex('^📝 Ver Minhas Tarefas$'), list_tasks))
    # MUDANÇA: Novo handler para o botão "Sobre"
    application.add_handler(MessageHandler(filters.Regex('^ℹ️ Sobre$'), about))
    application.add_handler(CallbackQueryHandler(handle_task_button, pattern='^(done|delete)_'))
    
    logging.info("Bot em modo profissional. Aguardando comandos e interações.")
    application.run_polling()

if __name__ == '__main__':
    main()
