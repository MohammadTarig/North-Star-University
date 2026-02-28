import json, random, logging, os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppConfig:
    """Application configuration"""
    TOTAL_MODULES = int(os.getenv('TOTAL_MODULES', '10'))
    DEFAULT_COOLDOWN = int(os.getenv('DEFAULT_COOLDOWN', '24'))
    MOTIVATION_FACT_CHANCE = float(os.getenv('MOTIVATION_FACT_CHANCE', '0.2'))

class TriggerType(Enum):
    """Main motivation triggers"""
    INACTIVITY = "inactivity"
    MILESTONE_COMPLETION = "milestone_completion"
    SKILL_MASTERY = "skill_mastery"

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class StudentMetrics:
    """Student metrics that will come from Core AI Engine"""
    student_id: str
    name: str
    last_activity: datetime
    modules_completed: List[str] = field(default_factory=list)
    modules_just_completed: List[str] = field(default_factory=list)  # Newly completed modules
    current_skill_levels: Dict[str, str] = field(default_factory=dict)
    previous_skill_levels: Dict[str, str] = field(default_factory=dict)  # To track skill changes
    skills_just_advanced: Dict[str, str] = field(default_factory=dict)  # Newly advanced skills
    overall_progress: float = 0.0
    learning_streak: int = 0
    time_since_last_activity: Optional[int] = None  # DAYS since last activity

@dataclass
class MotivationMessage:
    """Structure for motivation messages"""
    trigger_type: TriggerType
    priority: MessagePriority
    message: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    delivered: bool = False

class TriggerConfig:
    """Configuration for the main triggers""" 
    TRIGGER_SETTINGS = {
        TriggerType.INACTIVITY: {
            "enabled": True,
            "thresholds": [1, 3, 7],  # days
            "priority": MessagePriority.MEDIUM,
            "cooldown_hours": AppConfig.DEFAULT_COOLDOWN

        },
        TriggerType.MILESTONE_COMPLETION: {
            "enabled": True,
            "priority": MessagePriority.HIGH,
            "cooldown_hours": 0  # No cooldown - celebrate immediately
        },
        TriggerType.SKILL_MASTERY: {
            "enabled": True,
            "priority": MessagePriority.HIGH,
            "cooldown_hours": 0  # No cooldown - celebrate immediately
        }
    }

class MessageTemplates:
    """Dynamic message templates for the main triggers"""
    
    TEMPLATES = {
        TriggerType.INACTIVITY: {
            1: [  # 1 day
                "Hey {name}! 👋 Miss seeing your code! Ready for a quick session?",
                "Your coding journey awaits, {name}! Let's continue where we left off.",
                "{name}, your {last_skill} skills are calling! Jump back in whenever you're ready.",
                "It's been a day, {name}! Even 15 minutes of practice keeps you sharp!",
                "Hello {name}! Your next module is waiting for you. Let's make today count!"
            ],
            3: [  # 3 days
                "It's been 3 days, {name}! Your {last_skill} skills are waiting to level up!",
                "Missing you in the coding dojo, {name}! Come back and show us what you've got!",
                "{name}, even 10 minutes today can keep your momentum going! 🚀",
                "Hey {name}, consistency is key! Let's not let those {completed_count} completed modules go to waste!",
                "3 days away, {name}? Your {progress}% progress deserves to keep growing!"
            ],
            7: [  # 7 days
                "A whole week, {name}! Let's break that hiatus with something fun. New challenges await!",
                "{name}, a week without coding? Your brain misses the mental workout!",
                "Hey {name}, we've added new content since you left! Come check it out!",
                "7 days, {name}! Don't let your {last_skill} skills get rusty. Jump back in!",
                "{name}, you're {progress}% through the course! Too close to quit now!"
            ]
        },
        TriggerType.MILESTONE_COMPLETION: [
            "🎉 AMAZING! You've completed {module}, {name}! You're now {progress}% through your journey!",
            "Module {module} ✅ Conquered! Your dedication is inspiring, {name}!",
            "🌟 {module} mastered! You're unstoppable, {name}! Only {remaining} modules to go!",
            "Boom! 💥 {module} done! {name}, you're crushing this course!",
            "🏆 Achievement Unlocked: {module} completed! {name}, you're making incredible progress!",
            "Milestone reached! 🎯 {name} just completed {module}! That's {completed_count} modules down!",
            "{module} is DONE! 🚀 {name}, at this rate, you'll be an expert in no time!",
            "Victory! 🎊 {name} has conquered {module}! Your {progress}% completion rate is impressive!",
            "Another one bites the dust! {module} completed! Keep going, {name}!",
            "🔥 {module} module cleared! {name}, you're on fire! {remaining} more to become a master!"
        ],
        TriggerType.SKILL_MASTERY: [
            "🎯 Level UP! You're now {level} in {skill}! Keep this momentum going, {name}!",
            "From {old_level} to {level} in {skill}! {name}, that's what we call GROWTH! 📈",
            "Skill unlocked! 🔓 {name} has reached {level} status in {skill}!",
            "{name} + {skill} = {level} mastery! This is just the beginning!",
            "🌟 Major milestone! {name} has advanced to {level} in {skill}! Your hard work is paying off!",
            "SKILL UPGRADE! ⬆️ {name} is now {level} at {skill}! Previous level: {old_level}",
            "Incredible progress! {name} has mastered {skill} at {level} level! 🏅",
            "Breaking barriers! {name} advanced from {old_level} to {level} in {skill}! 💪",
            "🎊 Celebration time! {skill} skill leveled up to {level}! Way to go, {name}!",
            "Power up! 💥 {name}'s {skill} skills have evolved to {level}!"
        ]
    }
    # Additional motivational facts to append occasionally
    MOTIVATIONAL_FACTS = [
        "💡 Did you know? Consistent daily practice is the #1 predictor of coding success!",
        "💡 Fun fact: Most successful developers struggled with the same concepts you're learning now!",
        "💡 Remember: Every expert was once a beginner. You're on the right path!",
        "💡 Studies show that taking breaks actually improves learning retention!",
        "💡 Pro tip: Celebrating small wins leads to bigger achievements!"
    ]

class MotivationEngine:
    """Main motivation engine focused on 3 core triggers"""
    
    def __init__(self):
        self.config = TriggerConfig()
        self.templates = MessageTemplates()
        self.message_queue: List[MotivationMessage] = []
        self.cooldowns: Dict[str, Dict[TriggerType, datetime]] = defaultdict(dict)
        self.trigger_history: Dict[str, List[Dict]] = defaultdict(list)
        
    def evaluate_triggers(self, metrics: StudentMetrics) -> List[TriggerType]:
        """Evaluate which triggers should fire based on student metrics"""
        try:
            triggered = []
            
            # Check inactivity
            if self._check_inactivity(metrics):
                triggered.append(TriggerType.INACTIVITY)
            
            # Check milestone completion
            if self._check_milestone_completion(metrics):
                triggered.append(TriggerType.MILESTONE_COMPLETION)
            
            # Check skill mastery
            if self._check_skill_mastery(metrics):
                triggered.append(TriggerType.SKILL_MASTERY)
            
            # Apply cooldowns to prevent spam
            triggered = self._apply_cooldowns(metrics.student_id, triggered)
            
            return triggered
        except Exception as e:
            logger.error(f"Error evaluating triggers for {metrics.student_id}: {str(e)}")
            return []
    
    def _check_inactivity(self, metrics: StudentMetrics) -> bool:
        """Check if student has been inactive"""
        try:
            if not self.config.TRIGGER_SETTINGS[TriggerType.INACTIVITY]["enabled"]:
                return False
            
            # Calculate days inactive
            days_inactive = metrics.time_since_last_activity
            if days_inactive is None:
                days_inactive = (datetime.now() - metrics.last_activity).days
            
            thresholds = self.config.TRIGGER_SETTINGS[TriggerType.INACTIVITY]["thresholds"]
            return days_inactive in thresholds
        except Exception as e:
            logger.error(f"Error checking inactivity: {str(e)}")
            return False
    
    def _check_milestone_completion(self, metrics: StudentMetrics) -> bool:
        """Check if student completed any modules"""
        try:
            if not self.config.TRIGGER_SETTINGS[TriggerType.MILESTONE_COMPLETION]["enabled"]:
                return False
            
            return len(metrics.modules_just_completed) > 0
        except Exception as e:
            logger.error(f"Error checking milestone completion: {str(e)}")
            return False
    
    def _check_skill_mastery(self, metrics: StudentMetrics) -> bool:
        """Check if student advanced in any skills"""
        try:
            if not self.config.TRIGGER_SETTINGS[TriggerType.SKILL_MASTERY]["enabled"]:
                return False
            
            return len(metrics.skills_just_advanced) > 0
        except Exception as e:
            logger.error(f"Error checking skill mastery: {str(e)}")
            return False
    
    def _apply_cooldowns(self, student_id: str, triggers: List[TriggerType]) -> List[TriggerType]:
        """Apply cooldown periods to prevent message spam"""
        try:
            filtered = []
            now = datetime.now()
            
            for trigger in triggers:
                last_sent = self.cooldowns[student_id].get(trigger)
                if not last_sent:
                    filtered.append(trigger)
                    continue
                
                cooldown_hours = self.config.TRIGGER_SETTINGS[trigger]["cooldown_hours"]
                if cooldown_hours == 0 or (now - last_sent).total_seconds() / 3600 >= cooldown_hours:
                    filtered.append(trigger)
            
            return filtered
        except Exception as e:
            logger.error(f"Error applying cooldowns: {str(e)}")
            return triggers
    
    @lru_cache(maxsize=128)
    def _get_template(self, trigger: TriggerType, days_inactive: int = None) -> str:
        """Get a random template for the given trigger"""
        templates = self.templates.TEMPLATES[trigger]
        
        if trigger == TriggerType.INACTIVITY:
            if days_inactive >= 7:
                template_list = templates[7]
            elif days_inactive >= 3:
                template_list = templates[3]
            else:
                template_list = templates[1]
            
            return random.choice(template_list)
        else:
            return random.choice(templates)
    
    def generate_message(self, trigger: TriggerType, metrics: StudentMetrics) -> MotivationMessage:
        """Generate a personalized motivational message"""
        try:
            # Calculate days inactive for template selection
            days_inactive = None
            if trigger == TriggerType.INACTIVITY:
                days_inactive = metrics.time_since_last_activity
                if days_inactive is None:
                    days_inactive = (datetime.now() - metrics.last_activity).days
            
            # Get template
            template = self._get_template(trigger, days_inactive)
            
            # Build context for message formatting
            context = self._build_message_context(trigger, metrics)
            
            # Format message with context
            try:
                message = template.format(**context)
            except KeyError as e:
                logger.warning(f"Missing context key: {e}")
                message = template  # Use template as-is if formatting fails
            
            # Occasionally add a motivational fact
            if random.random() < AppConfig.MOTIVATION_FACT_CHANCE:
                fact = random.choice(self.templates.MOTIVATIONAL_FACTS)
                message += f"\n\n{fact}"
            
            # Create message object with appropriate priority
            priority = self.config.TRIGGER_SETTINGS[trigger]["priority"]
            
            return MotivationMessage(
                trigger_type=trigger,
                priority=priority,
                message=message,
                context=context
            )
        except Exception as e:
            logger.error(f"Error generating message: {str(e)}")
            # Return a fallback message
            return MotivationMessage(
                trigger_type=trigger,
                priority=MessagePriority.MEDIUM,
                message=f"Keep up the great work, {metrics.name}!",
                context={"name": metrics.name}
            )
    
    def _build_message_context(self, trigger: TriggerType, metrics: StudentMetrics) -> Dict[str, Any]:
        """Build context dictionary for message formatting"""
        try:
            context = {
                "name": metrics.name,
                "progress": round(metrics.overall_progress * 100, 1),
                "completed_count": len(metrics.modules_completed),
                "streak": metrics.learning_streak
            }
            
            # Add trigger-specific context
            if trigger == TriggerType.INACTIVITY:
                # Add last skill being worked on
                if metrics.current_skill_levels:
                    context["last_skill"] = list(metrics.current_skill_levels.keys())[-1]
                else:
                    context["last_skill"] = "coding"
            
            elif trigger == TriggerType.MILESTONE_COMPLETION:
                # Add module completion details
                if metrics.modules_just_completed:
                    context["module"] = metrics.modules_just_completed[-1]  # Most recent
                    context["remaining"] = max(0, AppConfig.TOTAL_MODULES - len(metrics.modules_completed))
                else:
                    context["module"] = "Introduction"
                    context["remaining"] = AppConfig.TOTAL_MODULES
            
            elif trigger == TriggerType.SKILL_MASTERY:
                # Add skill advancement details
                if metrics.skills_just_advanced:
                    skill = list(metrics.skills_just_advanced.keys())[0]
                    context["skill"] = skill
                    context["level"] = metrics.skills_just_advanced[skill]
                    
                    # Get previous level if available
                    if skill in metrics.previous_skill_levels:
                        context["old_level"] = metrics.previous_skill_levels[skill]
                    else:
                        # Default progression assumption
                        level_progression = ["Beginner", "Intermediate", "Advanced", "Expert"]
                        current_index = level_progression.index(context["level"]) if context["level"] in level_progression else 1
                        context["old_level"] = level_progression[max(0, current_index - 1)]
                else:
                    # Fallback values
                    context["skill"] = "Learning"
                    context["level"] = "Intermediate"
                    context["old_level"] = "Beginner"
            
            return context
        except Exception as e:
            logger.error(f"Error building message context: {str(e)}")
            return {"name": metrics.name, "progress": 0}
    
    def process_student(self, metrics: StudentMetrics) -> List[MotivationMessage]:
        """Main processing function for a student"""
        try:
            # Evaluate which triggers should fire
            triggers = self.evaluate_triggers(metrics)
            
            messages = []
            for trigger in triggers:
                # Generate personalized message
                message = self.generate_message(trigger, metrics)
                
                # Add to queue
                self.message_queue.append(message)
                messages.append(message)
                
                # Update cooldowns
                self.cooldowns[metrics.student_id][trigger] = datetime.now()
                
                # Log trigger history
                self.trigger_history[metrics.student_id].append({
                    "trigger": trigger.value,
                    "timestamp": datetime.now().isoformat(),
                    "message": message.message
                })
                
                logger.info(f"Generated {trigger.value} message for {metrics.name}")
            
            return messages
        except Exception as e:
            logger.error(f"Error processing student {metrics.student_id}: {str(e)}")
            return []
    
    # not currently in use
    def get_queued_messages(self, student_id: str = None, priority: MessagePriority = None) -> List[MotivationMessage]:
        """Get messages from queue, optionally filtered"""
        try:
            messages = self.message_queue
            
            if student_id:
                messages = [m for m in messages if hasattr(m, 'context') and m.context.get('student_id') == student_id]
            
            if priority:
                messages = [m for m in messages if m.priority == priority]
            
            # Sort by priority (highest first) and timestamp
            messages.sort(key=lambda x: (-x.priority.value, x.timestamp))
            
            return messages
        except Exception as e:
            logger.error(f"Error getting queued messages: {str(e)}")
            return []
    
    # not currently in use
    def mark_delivered(self, message: MotivationMessage):
        """Mark a message as delivered"""
        try:
            message.delivered = True
            if message in self.message_queue:
                self.message_queue.remove(message)
        except Exception as e:
            logger.error(f"Error marking message as delivered: {str(e)}")
    
    def get_trigger_history(self, student_id: str) -> List[Dict]:
        """Get trigger history for a student"""
        try:
            return self.trigger_history.get(student_id, [])
        except Exception as e:
            logger.error(f"Error getting trigger history: {str(e)}")
            return []

# not currently in use
class MotivationAPI:
    """HTTP (not websocket) API interface for the motivation engine"""
    
    def __init__(self):
        self.engine = MotivationEngine()
        
    def process_student_update(self, student_data: Dict) -> Dict:
        """
        Process student data and return triggered messages
        This will be called when Core AI Engine sends updates
        """
        try:
            # Convert dict to StudentMetrics
            metrics = self._dict_to_metrics(student_data)
            
            # Process student and generate messages
            messages = self.engine.process_student(metrics)
            
            # Format response
            response = {
                "student_id": metrics.student_id,
                "student_name": metrics.name,
                "triggers_activated": [msg.trigger_type.value for msg in messages],
                "messages": [
                    {
                        "type": msg.trigger_type.value,
                        "priority": msg.priority.value,
                        "priority_label": msg.priority.name,
                        "content": msg.message,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in messages
                ],
                "message_count": len(messages)
            }
            
            return response
        except Exception as e:
            logger.error(f"Error processing student update: {str(e)}")
            return {
                "error": "Failed to process student data",
                "student_id": student_data.get('student_id', 'unknown'),
                "messages": [],
                "message_count": 0
            }
    
    def get_pending_messages(self, student_id: str = None, priority: str = None) -> Dict:
        """Get all pending messages from queue"""
        try:
            # Convert priority string to enum if provided
            priority_enum = None
            if priority:
                priority_enum = MessagePriority[priority.upper()]
            
            messages = self.engine.get_queued_messages(student_id, priority_enum)
            
            return {
                "pending_messages": [
                    {
                        "type": msg.trigger_type.value,
                        "priority": msg.priority.value,
                        "priority_label": msg.priority.name,
                        "content": msg.message,
                        "timestamp": msg.timestamp.isoformat(),
                        "delivered": msg.delivered
                    }
                    for msg in messages
                ],
                "total_pending": len(messages)
            }
        except Exception as e:
            logger.error(f"Error getting pending messages: {str(e)}")
            return {"pending_messages": [], "total_pending": 0}
    
    def mark_message_delivered(self, message_index: int) -> Dict:
        """Mark a message as delivered"""
        try:
            messages = self.engine.get_queued_messages()
            if 0 <= message_index < len(messages):
                self.engine.mark_delivered(messages[message_index])
                return {"success": True, "message": "Message marked as delivered"}
            return {"success": False, "message": "Invalid message index"}
        except Exception as e:
            logger.error(f"Error marking message as delivered: {str(e)}")
            return {"success": False, "message": "Internal server error"}
    
    def get_student_history(self, student_id: str) -> Dict:
        """Get motivation history for a student"""
        try:
            history = self.engine.get_trigger_history(student_id)
            return {
                "student_id": student_id,
                "history": history,
                "total_triggers": len(history)
            }
        except Exception as e:
            logger.error(f"Error getting student history: {str(e)}")
            return {"student_id": student_id, "history": [], "total_triggers": 0}
    
    def _dict_to_metrics(self, data: Dict) -> StudentMetrics:
        """Convert dictionary to StudentMetrics object"""
        try:
            # Parse datetime fields if they're strings
            if "last_activity" in data and isinstance(data["last_activity"], str):
                data["last_activity"] = datetime.fromisoformat(data["last_activity"])
            
            # Ensure all required fields exist with defaults
            defaults = {
                "modules_completed": [],
                "modules_just_completed": [],
                "current_skill_levels": {},
                "previous_skill_levels": {},
                "skills_just_advanced": {},
                "overall_progress": 0.0,
                "learning_streak": 0,
                "time_since_last_activity": None
            }
            
            for key, default_value in defaults.items():
                if key not in data:
                    data[key] = default_value
            
            return StudentMetrics(**data)
        except Exception as e:
            logger.error(f"Error converting dict to metrics: {str(e)}")
            # Return minimal metrics object
            return StudentMetrics(
                student_id=data.get('student_id', 'unknown'),
                name=data.get('name', 'Unknown Student'),
                last_activity=datetime.now()
            )

# not currently in use
def test_api_interface():
    """Test the HTTP API interface with sample data"""
    print("\n" + "=" * 70)
    print(" API INTERFACE TEST")
    print("=" * 70)
    
    api = MotivationAPI()
    
    # Test 1: Inactivity trigger
    print("\n📝 Test 1: Inactivity Trigger")
    student_data = {
        "student_id": "api_test_001",
        "name": "John Doe",
        "last_activity": (datetime.now() - timedelta(days=3)).isoformat(),
        "time_since_last_activity": 3,
        "modules_completed": ["Module 1", "Module 2"],
        "current_skill_levels": {"Python": "Intermediate"},
        "overall_progress": 0.25
    }
    
    response = api.process_student_update(student_data)
    print("Response:", json.dumps(response, indent=2))
    
    # Test 2: Milestone completion
    print("\n📝 Test 2: Milestone Completion Trigger")
    student_data = {
        "student_id": "api_test_002",
        "name": "Jane Smith",
        "last_activity": datetime.now().isoformat(),
        "modules_completed": ["Module 1", "Module 2", "Module 3"],
        "modules_just_completed": ["Module 3"],
        "current_skill_levels": {"Python": "Advanced"},
        "overall_progress": 0.45
    }
    
    response = api.process_student_update(student_data)
    print("Response:", json.dumps(response, indent=2))
    
    # Test 3: Skill mastery
    print("\n📝 Test 3: Skill Mastery Trigger")
    student_data = {
        "student_id": "api_test_003",
        "name": "Bob Johnson",
        "last_activity": datetime.now().isoformat(),
        "modules_completed": ["Module 1", "Module 2", "Module 3", "Module 4"],
        "current_skill_levels": {"Python": "Expert", "Algorithms": "Advanced"},
        "previous_skill_levels": {"Python": "Advanced", "Algorithms": "Intermediate"},
        "skills_just_advanced": {"Python": "Expert"},
        "overall_progress": 0.60
    }
    
    response = api.process_student_update(student_data)
    print("Response:", json.dumps(response, indent=2))
    
    # Test 4: Get pending messages
    print("\n📝 Test 4: Get Pending Messages")
    pending = api.get_pending_messages()
    print(f"Total pending messages: {pending['total_pending']}")
