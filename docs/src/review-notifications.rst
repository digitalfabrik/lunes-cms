********************
Review notifications
********************

In addition to the emails experts receive about new content to review, staff
is notified about the review work of experts inside the CMS (see #1038). These
internal notifications are listed under *Notifications* in the admin, every
user only sees their own, and they can be marked as read or unread. A
notification sent to several users is stored once per user.

The recipients are the users who assigned the reviews in question. If the
assigning user of a review is unknown (e.g. deleted), all superusers are
notified instead. An expert is never notified about their own reviews.

There are three types of notifications:

* **Expert finished a review**: an expert has submitted the last pending
  review of a unit.
* **Expert flagged many words**: an expert has rejected or requested changes
  for ``LUNES_CMS_REVIEW_REJECTION_ALERT_THRESHOLD`` words of a unit (default:
  5). This is sent once per expert and unit.
* **Expert is behind on reviews**: an expert has reviews which are pending for
  more than ``LUNES_CMS_REVIEW_SLOW_EXPERT_DAYS`` days (default: 14). This is
  checked by

  .. code-block:: bash

      lunes-cms-cli notify_slow_experts

  which should run daily as a cronjob on the server. An expert is reported at
  most once within that number of days.
