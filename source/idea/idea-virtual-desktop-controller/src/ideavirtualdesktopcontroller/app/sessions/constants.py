from ideadatamodel import DayOfWeek

USER_SESSION_DB_HASH_KEY = 'owner'
USER_SESSION_DB_RANGE_KEY = 'idea_session_id'
USER_SESSION_DB_BASE_OS_KEY = 'base_os'
USER_SESSION_DB_CREATED_ON_KEY = 'created_on'
USER_SESSION_DB_UPDATED_ON_KEY = 'updated_on'
USER_SESSION_DB_SERVER_KEY = 'server'
USER_SESSION_DB_SOFTWARE_STACK_KEY = 'software_stack'
USER_SESSION_DB_NAME_KEY = 'name'
USER_SESSION_DB_DESCRIPTION_KEY = 'description'
USER_SESSION_DB_DCV_SESSION_ID_KEY = 'dcv_session_id'
USER_SESSION_DB_SESSION_TYPE_KEY = 'session_type'
USER_SESSION_DB_SESSION_TAGS_KEY = 'session_tags'
USER_SESSION_DB_STATE_KEY = 'state'
USER_SESSION_DB_SCHEDULE_KEYS = {
    DayOfWeek.MONDAY: 'monday_schedule',
    DayOfWeek.TUESDAY: 'tuesday_schedule',
    DayOfWeek.WEDNESDAY: 'wednesday_schedule',
    DayOfWeek.THURSDAY: 'thursday_schedule',
    DayOfWeek.FRIDAY: 'friday_schedule',
    DayOfWeek.SATURDAY: 'saturday_schedule',
    DayOfWeek.SUNDAY: 'sunday_schedule'
}
USER_SESSION_DB_HIBERNATION_KEY = 'hibernation_enabled'
USER_SESSION_DB_IS_LAUNCHED_BY_ADMIN_KEY = 'is_launched_by_admin'
USER_SESSION_DB_SESSION_LOCKED_KEY = 'locked'
USER_SESSION_DB_PROJECT_KEY = 'project'
USER_SESSION_DB_PROJECT_ID_KEY = 'project_id'
USER_SESSION_DB_PROJECT_NAME_KEY = 'name'
USER_SESSION_DB_PROJECT_TITLE_KEY = 'title'

USER_SESSION_DB_FILTER_BASE_OS_KEY = USER_SESSION_DB_BASE_OS_KEY
USER_SESSION_DB_FILTER_OWNER_KEY = USER_SESSION_DB_HASH_KEY
USER_SESSION_DB_FILTER_IDEA_SESSION_ID_KEY = USER_SESSION_DB_RANGE_KEY
USER_SESSION_DB_FILTER_STATE_KEY = USER_SESSION_DB_STATE_KEY
USER_SESSION_DB_FILTER_SESSION_TYPE_KEY = USER_SESSION_DB_SESSION_TYPE_KEY
USER_SESSION_DB_FILTER_INSTANCE_TYPE_KEY = 'instance_type'
USER_SESSION_DB_FILTER_SOFTWARE_STACK_ID_KEY = 'stack_id'
USER_SESSION_DB_FILTER_CREATED_ON_KEY = USER_SESSION_DB_CREATED_ON_KEY
USER_SESSION_DB_FILTER_UPDATED_ON_KEY = USER_SESSION_DB_UPDATED_ON_KEY

USER_SESSION_COUNTER_DB_HASH_KEY = 'idea_session_id'
USER_SESSION_COUNTER_DB_RANGE_KEY = 'counter_type'
USER_SESSION_COUNTER_DB_COUNTER_KEY = 'counter'
