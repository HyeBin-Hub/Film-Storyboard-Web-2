"""Feature flags and Streamlit widget defaults for the storyboard app."""

# =============================================================================================================================
# 1. Feature Flags
# =============================================================================================================================
ENABLE_MANUAL_REFERENCE_INPUT = False

ENABLE_PRESET_2A_RESULTS = False
ENABLE_PRESET_2B_RESULTS = False
ENABLE_PRESET_STEP3_RESULTS = False
ENABLE_PRESET_STEP4_RESULTS = False

# =============================================================================================================================
# 2. UI Defaults
# =============================================================================================================================
SKIN_DEFAULTS = {
    "natural_skin": 0.74,
    "bare_face": 0.75,
    "washed_face": 0.0,
    "dried_face": 0.0,
    "skin_details": 0.3,
    "skin_pores": 0.1,
    "dimples": 0.0,
    "wrinkles": 0.0,
    "freckles": 0.0,
    "moles": 0.0,
    "skin_imperfections": 0.0,
    "skin_acne": 0.0,
    "tanned_skin": 0.0,
    "eyes_details": 1.01,
    "iris_details": 0.0,
    "circular_iris": 0.0,
    "circular_pupil": 0.0,
}

BODY_TYPE_OPTIONS = [
    "Beefy", "Buxom", "Buff", "Chubby", "Curvy", "Fat", "Fit", "Flyweight",
    "Hefty", "Large", "Lanky", "Midweight", "Morbidly obese", "Muscular",
    "Obese", "Overweight", "Petite", "Plump", "Portly", "Rotund", "Short",
    "Skinny", "Slight", "Slim", "Small", "Stout", "Stocky", "Tall", "Thick",
    "Tiny", "Voluptuous", "Well-built", "Well-endowed", "Underweight",
]

FACE_SHAPE_OPTIONS = [
    "Circle", "Diamond", "Heart", "Heart with Pointed Chin", "Heart with Rounded Chin",
    "Heart with V-Shape Chin", "Inverted Triangle", "Long", "Oblong", "Oval", "Pear",
    "Rectangle", "Round", "Round with Defined Cheekbones", "Round with High Cheekbones",
    "Round with Soft Cheekbones", "Square", "Square Oval", "Square Round",
    "Square with Rounded Jaw", "Square with Sharp Jaw", "Square with Soft Jaw", "Triangle",
]

EXPRESSION_OPTIONS = [
    "Amused", "Angry", "Anxious", "Bored", "Calm", "Cautious", "Confused",
    "Contemptuous", "Content", "Curious", "Disappointed", "Disgusted", "Envious",
    "Excited", "Fearful", "Happy", "In love", "Nervous", "Peaceful", "Pensive",
    "Prideful", "Proud", "Relieved", "Sad", "Sarcastic", "Serene", "Serious",
    "Shy", "Silly", "Smiling", "Surprised", "Surprised and Amused",
]

EYES_COLOR_OPTIONS = ["Albino", "Amber", "Brown", "Dark Brown", "Black", "Hazel", "Blue", "Green", "Gray"]
EYES_SHAPE_OPTIONS = [
    "Almond Eyes Shape", "Asian Eyes Shape", "Close-Set Eyes Shape", "Deep Set Eyes Shape",
    "Downturned Eyes Shape", "Double Eyelid Eyes Shape", "Hooded Eyes Shape",
    "Monolid Eyes Shape", "Oval Eyes Shape", "Protruding Eyes Shape", "Round Eyes Shape",
    "Upturned Eyes Shape",
]
LIPS_COLOR_OPTIONS = [
    "Berry Lips", "Black Lips", "Blue Lips", "Brown Lips", "Burgundy Lips", "Coral Lips",
    "Glossy Red Lips", "Mauve Lips", "Orange Lips", "Peach Lips", "Pink Lips", "Plum Lips",
    "Purple Lips", "Red Lips", "Yellow Lips",
]
LIPS_SHAPE_OPTIONS = [
    "Biting Lips", "Bow-shaped Lips", "Closed Lips", "Cupid's Bow Lips",
    "Defined Cupid's Bow Lips", "Flat Cupid's Bow Lips", "Full Lips", "Heart-shaped Lips",
    "Large Lips", "Medium Lips", "Neutral Lips", "Parted Lips", "Plump Lips", "Pouting Lips",
    "Round Lips", "Small Lips", "Smiling Lips", "Soft Cupid's Bow Lips", "Thin Lips",
    "Upper Lip Mole Lips", "Wide Lips",
]
HAIR_STYLE_OPTIONS = [
    "Afro", "A-line bob", "Asymmetrical", "Balayage", "Bald", "Ballerina bun", "Bangs",
    "Beehive", "Beehivecut", "Bleached spikes", "Blunt bob", "Blunt", "Bob", "Bouffant",
    "Bowl", "Box braids", "Box fade", "Braided", "Braided bob", "Braided pigtails",
    "Brave shortcut with shaved sides", "Bushy", "Buzz", "Caesar", "Chignon", "Choppy",
    "Cloudy", "Cornrows", "Crew", "Curly", "Curly bob", "Curly Frizzy", "Curtain bangs",
    "Deep side part", "Double Bun", "Dreadlocks", "Faded afro", "Faux hawk",
    "Faux hawk short pixie", "Feathered", "Female bald", "Fishtail braids", "Flat topcut",
    "French bob", "French braids", "French twist", "Frohawk", "Hair ringlets", "High ponytail",
    "High skin fade", "Honey", "Italian bob", "Layered", "Lemonade braids", "Long bob",
    "Long with bangs", "Long pixie", "Long ponytail", "Long straight", "Loose Curly Afro",
    "Marmaid waves", "Micro braids", "Middle part ponytails", "Modern caesar", "Mohawk",
    "Multicolored", "Pastel", "Pigtails", "Pixie", "Platinum", "Pompadour", "Quiff",
    "Razor fade with curls", "Red", "Right side shaved", "Salt and pepper", "Shag", "Short curly",
    "Short curly pixie", "Short", "Short messy curls", "Shoulder Length with Bangs",
    "Shoulder length straight", "Side braid", "Side Part Comb-Overstyle With High Fade",
    "Side-swept bangs", "Side-swept fringe", "Sideswept pixie", "Smooth lob", "Space buns",
    "Spiky", "Stacked bob", "Stacked Curls in Short Bob", "Stitch braids", "Strawberry",
    "Strawberry blonde", "Sweeping pixie", "Taper fade with waves", "Taperedcut with shaved side",
    "Textured brush back", "Textured", "Tomboy", "Top Knot", "Twin braids", "Twintails",
    "Two dutch braids", "Undercut", "Updo", "Very long wave", "Waterfall braids", "Wavy",
    "Wavy bob", "Wavy with curtain bangs", "Wavy French Bob Vibes from 1920", "Wavy undercut",
]
HAIR_COLOR_OPTIONS = [
    "Auburn", "Black", "Blonde", "Burgundy", "Caramel", "Chestnut", "Chocolate", "Copper",
    "Dirty", "Gray", "Honey", "Jet Black", "Mahogany", "Multicolored", "Pastel", "Platinum",
    "Red", "Salt and pepper", "Silver", "Strawberry", "White",
]
NATIONALITY_OPTIONS = [
    "South Korean", "Korean", "East Asian",
    "Japanese", "Chinese"
]
HAIR_LENGTH_OPTIONS = ["-", "Short", "Medium", "Long"]
