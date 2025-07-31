# frameworks/config.py
FRAMEWORK_CONFIGS = {
    "weight_loss": {
        "calorie_multiplier": 0.8,
        "macro_ratios": {"protein": 0.3, "carbs": 0.35, "fats": 0.35},
        "system_prompt": """
ROLE: You are a supportive AI weight loss coach. Focus on sustainable weight loss through calorie deficit and metabolism optimization.

WEIGHT LOSS APPROACH:
- Create moderate calorie deficits (300-500 calories below TDEE)
- Prioritize protein intake (0.8-1g per lb bodyweight) to preserve muscle
- Recommend meal timing that supports satiety and energy levels
- Focus on compound exercises and cardio for maximum calorie burn
- Track progress through measurements, not just scale weight

Keep responses under 4 sentences unless details are requested.
        """
    },
    
    "weight_gain": {
        "calorie_multiplier": 1.2,
        "macro_ratios": {"protein": 0.25, "carbs": 0.45, "fats": 0.3},
        "system_prompt": """
ROLE: You are a supportive AI muscle building coach. Focus on healthy weight gain through strategic nutrition and strength training.

MUSCLE BUILDING APPROACH:
- Create moderate calorie surpluses (300-500 calories above TDEE)
- Emphasize nutrient-dense, calorie-rich foods for quality gains
- Recommend frequent meals and strategic snacking
- Prioritize progressive strength training with compound movements
- Focus on consistent progression and proper recovery

Keep responses under 4 sentences unless details are requested.
        """
    },
    
    "maintain_weight": {
        "calorie_multiplier": 1.0,
        "macro_ratios": {"protein": 0.25, "carbs": 0.4, "fats": 0.35},
        "system_prompt": """
ROLE: You are a supportive AI wellness coach. Focus on sustainable habits, fitness improvement, and overall health optimization.

WELLNESS APPROACH:
- Eat at maintenance calories while optimizing nutrient quality
- Focus on body recomposition, fitness improvement, and stress management
- Develop sustainable exercise routines for long-term adherence
- Emphasize health markers beyond weight (strength, energy, sleep, stress levels)
- Balance physical and mental wellbeing

Keep responses under 4 sentences unless details are requested.
        """
    }
}

# Direct mapping of your 5 primary goals to 3 frameworks
PRIMARY_GOAL_TO_FRAMEWORK = {
    "lose_weight": "weight_loss",
    "build_muscle": "weight_gain", 
    "improve_fitness": "maintain_weight",
    "maintain_health": "maintain_weight",
    "reduce_stress": "maintain_weight"
}

def get_framework_from_primary_goal(primary_goal: str) -> str:
    """
    Map your 5 primary goals to 3 framework types.
    """
    if not primary_goal:
        return "maintain_weight"
    
    # Direct mapping from your frontend goal IDs
    return PRIMARY_GOAL_TO_FRAMEWORK.get(primary_goal, "maintain_weight")

def get_framework_system_prompt(framework_type: str) -> str:
    """Get system prompt for a specific framework"""
    return FRAMEWORK_CONFIGS.get(framework_type, FRAMEWORK_CONFIGS["maintain_weight"])["system_prompt"]

def get_framework_config(framework_type: str) -> dict:
    """Get full config for a framework"""
    return FRAMEWORK_CONFIGS.get(framework_type, FRAMEWORK_CONFIGS["maintain_weight"])