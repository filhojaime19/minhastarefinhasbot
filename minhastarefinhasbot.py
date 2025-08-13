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
        if update.message.text == '/cancelar':
            await update.message.reply_text(
                "❌ Operação cancelada.", 
                reply_markup=get_main_keyboard()
            )
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
                "👉 *Dica:* Você pode tirar uma foto direto do Telegram!",
                parse_mode='Markdown',
                reply_markup=get_cancel_keyboard()
            )
            return GET_ATTACHMENT
            
        elif query.data == 'add_link':
            await query.edit_message_text(
                "🔗 *Adicionar Link*\n\nPor favor, envie o link completo (começando com http:// ou https://)",
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
                "❌ Tipo de anexo não suportado.\n\nPor favor, envie uma foto ou vídeo.",
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
        link_text = update.message.text
        
        # Validação básica de URL
        if not (link_text.startswith('http://') or link_text.startswith('https://')):
            await update.message.reply_text(
                "❌ Por favor, envie um link válido (começando com http:// ou https://)",
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
            "❌ Ocorreu um erro. Tente novamente mais tarde.",
            reply_markup=get_main_keyboard()
        )

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
            await query.edit_message_text("✅ *Tarefa concluída com sucesso!*\n\nParabéns por manter-se organizado! 👍", parse_mode='Markdown')
            logger.info(f"Tarefa {task_id} concluída")
        elif action == "delete":
            cursor.execute("DELETE FROM tarefas WHERE id = ?", (task_id,))
            await query.edit_message_text("🗑️ *Tarefa apagada permanentemente*\n\nEsperamos que tenha concluído!", parse_mode='Markdown')
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
        help_text = """🤖 *Bot de Tarefas Pessoal*

📝 *Comandos disponíveis:*
• /start - Iniciar o bot
• /help - Mostrar esta ajuda
• /cancelar - Cancelar operação atual

💡 *Como usar:*
1. Clique em "➕ Nova Tarefa"
2. Digite o título da tarefa
3. Opcionalmente, adicione foto, vídeo ou link
4. Veja suas tarefas em "📝 Minhas Tarefas"
5. Conclua ou apague tarefas usando os botões

✨ *Diferenciais:*
• Interface profissional e intuitiva
• Suporte para anexos diversos
• Opção de voltar e cancelar a qualquer momento"""
        
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
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

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Handler da conversa para adicionar tarefas
        add_task_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^➕ Nova Tarefa$'), start_add_task)],
            states={
                GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_task_title)],
                GET_ATTACHMENT: [
                    CallbackQueryHandler(handle_attachment_choice, pattern='^(add_media|add_link|skip_attachment|back_to_title|cancel_operation)$'),
                    MessageHandler(filters.PHOTO | filters.VIDEO, get_attachment),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_link),
                ],
                GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            },
            fallbacks=[CommandHandler('cancelar', cancel)],
        )

        application.add_handler(add_task_conv_handler)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cancelar", cancel))
        application.add_handler(MessageHandler(filters.Regex('^📝 Minhas Tarefas$'), list_tasks))
        application.add_handler(MessageHandler(filters.Regex('^❓ Sobre$'), about))
        application.add_handler(CallbackQueryHandler(handle_task_button, pattern='^(done|delete)_'))
        
        logger.info("Bot em modo profissional. Aguardando comandos e interações.")
        application.run_polling()
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar o bot: {e}")
        raise

if __name__ == '__main__':
    main()
