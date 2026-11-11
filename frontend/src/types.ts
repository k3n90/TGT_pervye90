export type Role = "hr" | "mentor" | "manager" | "director";

export interface Account {
  username: string;
  full_name: string;
  role: Role;
  role_label: string;
  title: string;
  location_name: string;
}

export interface SessionUser {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  role_label: string;
  title: string;
  location_name: string | null;
  nav: string[];
}

export interface Person {
  id: number;
  full_name: string;
  role: Role;
  title: string;
}

export interface CardBrief {
  id: number;
  full_name: string;
  position_name: string;
  track_code: string;
  track_name: string;
  location_name: string;
  department_name: string;
  start_date: string;
  probation_end_date: string;
  stage: string;
  stage_label: string;
  mentor_name: string | null;
  manager_name: string;
  admission: string;
  admission_label: string;
  red_count: number;
  yellow_count: number;
  separation_started: boolean;
}

export interface CheckItem {
  id: number;
  code: string;
  day: number;
  title: string;
  is_critical: boolean;
  mark: "yes" | "not_yet" | null;
  fail_count: number;
  can_mark: boolean;
  due_date: string;
}

export interface Checkpoint {
  day: number;
  due_date: string;
  is_final: boolean;
  label: string;
  status: "done" | "done_late" | "skipped" | "overdue" | "open" | "future";
  completed_at: string | null;
}

export interface Pulse {
  day: number;
  due_date: string;
  q1: Answer | null;
  q2: Answer | null;
  q3: Answer | null;
  comment: string;
  recorded_at: string | null;
  can_record: boolean;
}

export type Answer = "yes" | "mid" | "no";

export interface Signal {
  id: number;
  code: string;
  severity: "red" | "yellow";
  title: string;
  detail: string;
  status: string;
  owner: Person | null;
  due_date: string | null;
  opened_at: string | null;
  recheck_date: string | null;
  resolution: string | null;
  resolution_label: string;
  comment: string;
  resolved_at: string | null;
  overdue: boolean;
  allow_fixed: boolean;
  can_resolve: boolean;
  needs_action: boolean;
}

export interface CardDetail extends CardBrief {
  position_code: string;
  probation_days: number;
  first_shift_schedule: string;
  hire_source: string;
  shared_warehouse: boolean;
  critical_count: number;
  critical_limit: number;
  mentor: Person | null;
  manager: Person | null;
  admission_note: string;
  admission_date: string | null;
  day30_choice: string | null;
  day30_choice_label: string;
  day30_reason: string;
  day30_recheck_date: string | null;
  day60_stable: boolean | null;
  day60_note: string;
  probation_decision: string | null;
  probation_decision_label: string;
  probation_decision_comment: string;
  probation_decision_date: string | null;
  transfer_title: string;
  dismissed_date: string | null;
  questions: { code: string; text: string }[];
  answer_labels: Record<Answer, string>;
  items: CheckItem[];
  checkpoints: Checkpoint[];
  pulses: Pulse[];
  signals: Signal[];
  resolved_signals: Signal[];
  waiting: Signal[];
  events: { at: string; actor: string; text: string }[];
  permissions: {
    edit_items: boolean;
    assign_mentor: boolean;
    edit_schedule: boolean;
    admission: boolean;
    day30: boolean;
    day60: boolean;
    decision: boolean;
    decision_hint: string;
  };
}

export interface QueueResponse {
  items: (CardBrief & { signal: Signal })[];
  waiting: (CardBrief & { signal: Signal })[];
}

export interface Ratio {
  num: number;
  den: number;
  hint: string;
}

export interface Summary {
  today: string;
  month_label: string;
  scope_note: string;
  operations: {
    starts: number;
    open_reds: number;
    open_reds_overdue: number;
    checkpoints_closed: number;
    left_under_30: number;
    left_under_90: number;
    by_department: {
      name: string;
      starts: number;
      open_reds: number;
      left_under_30: number;
      left_under_90: number;
      admitted: string;
    }[];
  };
  pilot: {
    mentor_before_day1: Ratio;
    day1_and_14_on_time: Ratio;
    independent_by_14: Ratio;
    reds_in_two_days: Ratio;
    decisions_recorded: Ratio;
  };
  baseline: {
    hired: number;
    left: number;
    left_under_30: number;
    left_under_90: number;
    share_leavers_under_90: number | null;
    survival_30: number | null;
    survival_90: number | null;
    caption: string;
    by_department: {
      name: string;
      hired: number;
      left: number;
      left_under_30: number;
      left_under_90: number;
      share_leavers_under_90: number | null;
      survival_30: number | null;
      survival_90: number | null;
    }[];
  };
}

export interface Meta {
  locations: { id: number; name: string; department_code: string }[];
  positions: { code: string; name: string; track_code: string; track_name: string }[];
  people: { id: number; full_name: string; role: Role; title: string; location_id: number | null }[];
  sources: string[];
  probation_options: { days: number; label: string }[];
  questions: { code: string; text: string }[];
}

export interface TrackTemplate {
  code: string;
  name: string;
  critical_count: number;
  critical_limit: number;
  items: {
    id: number;
    title: string;
    day: number;
    is_critical: boolean;
    include_mode: string;
    position_code: string | null;
    is_active: boolean;
  }[];
}
