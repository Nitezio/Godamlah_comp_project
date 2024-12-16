import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import Update
from jamaibase import JamAI, protocol as p

# Initialize JamAI
jamai = JamAI(api_key="jamai_pat_54ad365b238a825e6cadd977dd4d4ef85ad83cb0d82d3d1f",
              project_id="proj_89c431f8f87cde88cd504be4")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define API Key for the bot
API_KEY = "7348521172:AAFRrJdL1hMXymkW4VeawQJ15HwdeF3VtQc"

# Dictionary to store harmful message analysis results
harmful_messages = {}

async def monitor_conversation(update: Update, context: CallbackContext):
    """Monitor conversations and perform the necessary checks."""
    try:
        # Fetch the chat and user information
        chat = update.message.chat
        user = update.message.from_user

        # Log the incoming message
        logger.info(f"Message from {user.first_name} ({user.id}): {update.message.text}")

        # Process the message with JamAI by adding it to the table for analysis
        completion = jamai.add_table_rows(
            "action",  # Table name for the analysis
            p.RowAddRequest(
                table_id="ChatGuardAI_3.0",  # The table id you are using
                data=[{"Message": update.message.text}],  # Add the message text
                stream=False
            )
        )

        # Process the outputs
        if completion.rows and len(completion.rows) > 0:
            output_row = completion.rows[0].columns  # Access the first row's columns

            # Safely extract fields from the output_row
            label = output_row.get("Label", None)
            message = output_row.get("Message", None)
            level = output_row.get("Level", None)
            report = output_row.get("Report", None)  # Extract report if available

            # Check if the label indicates harmful content
            if label and label.text and "harmful" in label.text.lower():
                harmful_messages[chat.id] = {
                    "label": label.text,
                    "message": update.message.text,  # Ensure we use the original message text
                    "level": level.text if level else 'N/A',
                    "report": report.text if report else None,  # Only add report if available
                }

                # Send the notification about harmful message detection
                notification_message = (
                    f"⚠️ Harmful Message Report:\n"
                    f"🏷️ Label: {label.text}\n"
                    f"📝 Message: \"{update.message.text}\"\n"  # Use the original message text
                    f"📈 Level: {level.text if level else 'N/A'}\n\n"
                    "Type /givereport for a detailed analysis."
                )
                await context.bot.send_message(chat.id, notification_message)
        else:
            logger.warning("No rows returned from JamAI.")

    except Exception as e:
        logger.error(f"Error while monitoring conversation: {e}")
        await context.bot.send_message(update.message.chat.id, "❌ An error occurred while processing the message.")

async def start(update: Update, context: CallbackContext):
    """Send a welcome message when the bot starts."""
    await update.message.reply_text("Welcome! I'm ChatGuardAI. I will monitor conversations.")


async def give_report(update: Update, context: CallbackContext):
    """Send the detailed report for the last harmful message detected."""
    chat_id = update.message.chat.id
    if chat_id in harmful_messages:
        report = harmful_messages[chat_id]

        # Safely extract 'report' if available
        report_message = report.get('report', "No detailed report available.")

        # Ensure the message fits Telegram's character limit
        if len(report_message) > 4096:
            chunks = [report_message[i:i + 4000] for i in range(0, len(report_message), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(report_message)
    else:
        await update.message.reply_text("❌ No harmful message detected in this chat.")


async def handle_message(update: Update, context: CallbackContext):
    """Handle incoming messages."""
    await monitor_conversation(update, context)

def main():
    """Start the bot."""
    # Create the application
    application = Application.builder().token(API_KEY).build()

    # Command handler for /start command
    application.add_handler(CommandHandler("start", start))

    # Command handler for /givereport
    application.add_handler(CommandHandler("givereport", give_report))

    # Message handler to monitor messages in the group
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
