"""Configuration module for promotions bot."""

# Add your promotion configurations here
# Each promotion requires: id, name, caption, media list, admin_username
PROMOTIONS = [
    {
        'id': 'promo_001',
        'name': 'Summer Sale',
        'caption': '*☀️ Summer Sale* \n\nGet up to *30% off* on all summer items!\n\nDon\'t miss out on this amazing offer!',
        'media': [],  # Add image/video paths here: ['path/to/image.jpg', 'path/to/video.mp4']
        'admin_username': 'ec_admin',  # Replace with actual admin username
    },
    {
        'id': 'promo_002',
        'name': 'Back to School',
        'caption': '*📚 Back to School Special*\n\nSpecial discount on school supplies and clothing\n\n*25% off* everything!',
        'media': [],
        'admin_username': 'ec_admin',
    },
    {
        'id': 'promo_003',
        'name': 'Flash Deal',
        'caption': '*⚡ Flash Deal*\n\nLimited time offer on selected products\n\n*50% off* - Hurry, while supplies last!',
        'media': [],
        'admin_username': 'ec_admin',
    },
    {
        'id': 'promo_004',
        'name': 'Weekend Special',
        'caption': '*🎉 Weekend Special*\n\nExclusive weekend promotion for all members\n\n*15% extra savings* this weekend!',
        'media': [],
        'admin_username': 'ec_admin',
    },
    {
        'id': 'promo_005',
        'name': 'New Year Clearance',
        'caption': '*🎊 New Year Clearance*\n\nYear-end clearance sale on all categories\n\n*40% off* selected items!',
        'media': [],
        'admin_username': 'ec_admin',
    },
    {
        'id': 'promo_006',
        'name': 'Loyalty Rewards',
        'caption': '*💎 Loyalty Rewards*\n\nExtra savings for our loyal customers\n\n*20% off* your next purchase!',
        'media': [],
        'admin_username': 'ec_admin',
    },
]

# Promotion interval in seconds (7200 = 2 hours)
PROMOTION_INTERVAL = 7200
