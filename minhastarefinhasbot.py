# --- INÍCIO DO CÓDIGO COMPLETO ---

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ETAPA 1: Configuração do logging para depuração.
# Isso ajuda a ver informações e erros no seu terminal enquanto o bot está rodando.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ETAPA 2: Definição dos "estados" da conversa.
# Pense neles como as etapas do diálogo: primeiro pedimos o tema, depois o prazo.
GET_TEMA, GET_PRAZO = range(2)

# ETAPA 3: Definição das funções que controlam a conversa.

async def novatarefa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função que INICIA a conversa quando o usuário envia /novatarefa."""
    await update.message.reply_text(
        "Olá! Vamos criar uma nova tarefa.\n"
        "Primeiro, me diga qual é o tema da tarefa. "
        "Você pode cancelar a qualquer momento enviando /cancelar."
    )
    # Informa ao bot que a próxima etapa (estado) é esperar pelo TEMA.
    return GET_TEMA


async def get_tema(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função que é executada DEPOIS que o usuário envia o tema."""
    # Guarda o texto que o usuário enviou.
    tema_da_tarefa = update.message.text
    
    # Armazena o tema para usar mais tarde.
    context.user_data['tema'] = tema_da_tarefa
    
    logger.info(f"Tema da tarefa recebido: {tema_da_tarefa}")

    # Pede a próxima informação (o prazo).
    await update.message.reply_text(
        f"Entendido! O tema é '{tema_da_tarefa}'.\nAgora, qual é o prazo para a entrega?"
    )
    
    # Informa ao bot que a próxima etapa (estado) é esperar pelo PRAZO.
    return GET_PRAZO


async def get_prazo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função que é executada DEPOIS que o usuário envia o prazo."""
    prazo_da_tarefa = update.message.text
    context.user_data['prazo'] = prazo_da_tarefa
    
    logger.info(f"Prazo da tarefa recebido: {prazo_da_tarefa}")

    # Pega o tema que foi salvo antes.
    tema = context.user_data['tema']
    
    # Envia a mensagem de confirmação final.
    await update.message.reply_text(
        "Ótimo! Tarefa criada com sucesso:\n"
        f"📝 *Tema:* {tema}\n"
        f"🗓️ *Prazo:* {prazo_da_tarefa}",
        parse_mode='Markdown'
    )

    # Limpa a memória da conversa.
    context.user_data.clear()
    
    # Informa ao bot que a conversa ACABOU.
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função para CANCELAR a conversa a qualquer momento."""
    await update.message.reply_text(
        "Criação de tarefa cancelada."
    )
    # Limpa a memória e termina a conversa.
    context.user_data.clear()
    return ConversationHandler.END


# ETAPA 4: A função principal (main) que monta e executa o bot.

def main() -> None:
    """Função principal que organiza e inicia o bot."""
    
    # Substitua "SEU_TOKEN_AQUI" pelo token real do seu bot, obtido com o @BotFather.
    application = Application.builder().token("SEU_TOKEN_AQUI").build()

    # Cria o ConversationHandler, que é o gerenciador de toda a conversa.
    conv_handler = ConversationHandler(
        # Ponto de entrada: como a conversa começa.
        entry_points=[CommandHandler("novatarefa", novatarefa)],
        
        # Estados: o que fazer em cada etapa da conversa.
        states={
            GET_TEMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tema)],
            GET_PRAZO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prazo)],
        },
        
        # Fallbacks: como sair da conversa no meio do caminho.
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    # Adiciona o gerenciador de conversa ao bot.
    application.add_handler(conv_handler)

    # Inicia o bot. Ele ficará rodando e esperando por mensagens.
    print("Bot iniciado e rodando. Pressione Ctrl+C para parar.")
    application.run_polling()

# ETAPA 5: Linha padrão que executa a função main() quando o script é iniciado.
if __name__ == "__main__":
    main()

# --- FIM DO CÓDIGO COMPLETO ---
