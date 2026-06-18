"""Shared styling elements for embeds and messages across the bot"""

# Vibrant Color Palette
COLORS = {
    # Main theme colors
    "PRIMARY": 0x5865F2,    # Discord Blurple
    "SUCCESS": 0x57F287,    # Bright Green
    "WARNING": 0xFEE75C,    # Bright Yellow
    "ERROR": 0xED4245,      # Bright Red
    "INFO": 0x5BC0DE,       # Light Blue
    
    # Additional fun colors
    "PINK": 0xFFC0CB,       # Baby Pink
    "PURPLE": 0x9B59B6,     # Rich Purple
    "ORANGE": 0xE67E22,     # Vibrant Orange
    "TEAL": 0x1ABC9C,       # Turquoise
    "GOLD": 0xF1C40F,       # Gold
    "SILVER": 0x95A5A6,     # Silver
    "BRONZE": 0xCD7F32,     # Bronze
    "EMERALD": 0x2ECC71,    # Emerald Green
    "RUBY": 0xE74C3C,       # Ruby Red
    "SAPPHIRE": 0x3498DB,   # Sapphire Blue
}

# Emojis by category
EMOJIS = {
    # Currency & Economy
    "MONEY": "💰",
    "COINS": "🪙",
    "GEM": "💎",
    "DOLLAR": "💵",
    "BANK": "🏦",
    "WALLET": "👛",
    "RICH": "🤑",
    "CHART_UP": "📈",
    "CHART_DOWN": "📉",
    
    # Actions
    "ADD": "➕",
    "REMOVE": "➖",
    "CHECK": "✅",
    "CROSS": "❌",
    "WARNING": "⚠️",
    "ALERT": "🚨",
    "SPARKLE": "✨",
    "STAR": "⭐",
    "FIRE": "🔥",
    "MAGIC": "🪄",
    "LOADING": "⏳",
    "INFO": "ℹ️",
    
    # Items & Objects
    "CLOCK": "⏰",
    "LOCK": "🔒",
    "KEY": "🔑",
    "BOOK": "📚",
    "SCROLL": "📜",
    "TOOL": "🔧",
    "GIFT": "🎁",
    "MAIL": "📧",
    "TROPHY": "🏆",
    "MEDAL_GOLD": "🥇",
    "MEDAL_SILVER": "🥈",
    "MEDAL_BRONZE": "🥉",
    "DATABASE": "🗄️",
    
    # Faces & People
    "SMILE": "😊",
    "SAD": "😢",
    "THINK": "🤔",
    "SHOCK": "😱",
    "COOL": "😎",
    "ROBOT": "🤖",
    "MAGE": "🧙",
}

# Formatting helpers
def format_currency(amount, symbol="$"):
    """Format a currency amount with thousand separators and 2 decimal places"""
    return f"{symbol}{amount:,.2f}"

def get_rank_emoji(position):
    """Return appropriate emoji based on leaderboard position"""
    if position == 1:
        return EMOJIS["MEDAL_GOLD"]
    elif position == 2:
        return EMOJIS["MEDAL_SILVER"]
    elif position == 3:
        return EMOJIS["MEDAL_BRONZE"]
    elif position <= 10:
        return EMOJIS["STAR"]
    else:
        return "▫️" 