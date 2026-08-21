# Canvas Calendar Sync

Automatically synchronize Canvas assignments with Google Calendar. Each Canvas course will have its own Google Calendar so classes can be displayed, hidden, and colored independently. The application will detect new, changed, and removed assignments and keep Google Calendar synchronized without creating duplicate events.

# 0.1 Foundations

Set up the Python project and establish the basic application structure.

## 0.1.1 Project Setup

Create the initial project and development environment.

### 0.1.1.1 Python Project

Set up the Python application and its dependencies.

#### 0.1.1.1.1 Create Python Project

Create the initial Python project structure.

**End Goal:**

- A working Python project that can be run locally.

**Work Steps:**

- [x] Create the project directory
- [x] Create a virtual environment
- [ ] Create `pyproject.toml`
- [ ] Create the application package
- [ ] Create the initial entry point
- [ ] Add `.gitignore`

#### 0.1.1.1.2 Create GitHub Repository

Create the GitHub repository for the project.

**End Goal:**

- The project is stored in a GitHub repository.

**Work Steps:**

- [ ] Create the repository
- [ ] Connect the local project to GitHub
- [ ] Commit the initial project
- [ ] Push the project to GitHub

## 0.1.2 Configuration

Create a safe configuration system for credentials and application settings.

### 0.1.2.1 Secrets

Keep Canvas and Google credentials outside the source code.

#### 0.1.2.1.1 Configure Environment Variables

Add support for local secrets.

**End Goal:**

- Credentials can be used without storing them in Git.

**Work Steps:**

- [ ] Add environment-variable support
- [ ] Add Canvas base URL setting
- [ ] Add Canvas token setting
- [ ] Add Google credential settings
- [ ] Add example configuration
- [ ] Ensure secrets are ignored by Git

# 0.2 Canvas Connection

Connect the application to Canvas and retrieve the student's Canvas information.

## 0.2.1 Authentication

Establish authenticated access to Canvas.

### 0.2.1.1 Canvas API Client

Create the reusable Canvas connection.

#### 0.2.1.1.1 Connect to Canvas

Authenticate using a Canvas access token.

**End Goal:**

- The application can successfully make an authenticated Canvas API request.

**Work Steps:**

- [ ] Load the Canvas URL
- [ ] Load the access token
- [ ] Create authorization headers
- [ ] Request the current Canvas user
- [ ] Handle authentication failures
- [ ] Confirm successful connection

## 0.2.2 Courses

Retrieve the student's Canvas courses.

### 0.2.2.1 Course Reader

Read active courses from Canvas.

#### 0.2.2.1.1 Retrieve Courses

Get the student's current courses.

**End Goal:**

- The application can display the student's active Canvas courses.

**Work Steps:**

- [ ] Request enrolled courses
- [ ] Read course IDs
- [ ] Read course names
- [ ] Identify active courses
- [ ] Ignore irrelevant or concluded courses
- [ ] Display the course list

## 0.2.3 Assignments

Retrieve assignments for each Canvas course.

### 0.2.3.1 Assignment Reader

Read assignment information from Canvas.

#### 0.2.3.1.1 Retrieve Assignments

Retrieve assignments for the student's courses.

**End Goal:**

- The application can retrieve assignments and their important metadata.

**Work Steps:**

- [ ] Request assignments for each course
- [ ] Read assignment IDs
- [ ] Read assignment names
- [ ] Read due dates
- [ ] Read availability dates
- [ ] Read assignment URLs
- [ ] Associate assignments with courses

#### 0.2.3.1.2 Handle Assignment States

Determine which assignments should be synchronized.

**End Goal:**

- Published future assignments can be synchronized even when they are not yet unlocked.

**Work Steps:**

- [ ] Identify published assignments
- [ ] Detect locked assignments
- [ ] Detect assignments without due dates
- [ ] Detect past assignments
- [ ] Define synchronization rules for each state

# 0.3 Google Calendar Connection

Connect the application to Google Calendar.

## 0.3.1 Authentication

Establish Google Calendar API access.

### 0.3.1.1 Google API Client

Create the reusable Google Calendar connection.

#### 0.3.1.1.1 Connect to Google Calendar

Authenticate with Google and verify Calendar access.

**End Goal:**

- The application can read and write Google Calendar data.

**Work Steps:**

- [ ] Configure Google API credentials
- [ ] Implement OAuth authorization
- [ ] Store authorization safely
- [ ] Connect to the Calendar API
- [ ] Retrieve available calendars
- [ ] Handle authentication failures

# 0.4 Course Calendars

Create and manage a separate Google Calendar for each Canvas course.

## 0.4.1 Calendar Mapping

Associate Canvas courses with Google calendars.

### 0.4.1.1 Course Calendar Manager

Create and identify course calendars.

#### 0.4.1.1.1 Create Course Calendars

Create a Google Calendar for each Canvas course.

**End Goal:**

- Each Canvas course has its own Google Calendar.

**Work Steps:**

- [ ] Check for an existing course calendar
- [ ] Create missing calendars
- [ ] Store Canvas course IDs with calendar mappings
- [ ] Prevent duplicate calendars
- [ ] Display created and existing mappings

#### 0.4.1.1.2 Preserve Calendar Preferences

Avoid overwriting user-controlled Google Calendar settings.

**End Goal:**

- Users can customize course calendars without the sync undoing those choices.

**Work Steps:**

- [ ] Allow users to choose calendar colors in Google
- [ ] Do not overwrite calendar colors during sync
- [ ] Preserve visibility preferences
- [ ] Preserve notification preferences

# 0.5 Assignment Synchronization

Synchronize Canvas assignments with Google Calendar.

## 0.5.1 Event Creation

Create Google Calendar events from Canvas assignments.

### 0.5.1.1 Assignment Events

Convert Canvas assignments into calendar events.

#### 0.5.1.1.1 Create Assignment Events

Create events for assignments that do not already exist.

**End Goal:**

- New Canvas assignments automatically appear on the appropriate Google Calendar.

**Work Steps:**

- [ ] Create an event on the correct course calendar
- [ ] Use the assignment name as the event title
- [ ] Use the Canvas due date as the event time
- [ ] Add the course name
- [ ] Add the Canvas assignment link
- [ ] Include availability information when useful
- [ ] Store the Canvas assignment ID with the event

## 0.5.2 Duplicate Prevention

Ensure repeated synchronization does not create duplicate events.

### 0.5.2.1 Assignment Identity

Use Canvas assignment IDs to identify synchronized events.

#### 0.5.2.1.1 Prevent Duplicate Events

Find existing Google events before creating new ones.

**End Goal:**

- Running synchronization repeatedly never creates duplicate assignment events.

**Work Steps:**

- [ ] Store Canvas assignment ID in Google event metadata
- [ ] Search for an existing assignment event
- [ ] Create an event only when none exists
- [ ] Test repeated synchronization

## 0.5.3 Assignment Updates

Update Google Calendar when Canvas assignments change.

### 0.5.3.1 Change Detection

Compare Canvas assignments with existing calendar events.

#### 0.5.3.1.1 Update Changed Assignments

Modify calendar events when assignment information changes.

**End Goal:**

- Google Calendar reflects changes made by teachers in Canvas.

**Work Steps:**

- [ ] Detect changed assignment names
- [ ] Detect changed due dates
- [ ] Detect changed availability dates
- [ ] Detect changed course information
- [ ] Update the existing Google event
- [ ] Avoid changing events that have not changed

## 0.5.4 Removed Assignments

Handle assignments that disappear from Canvas.

### 0.5.4.1 Removal Detection

Identify previously synchronized assignments that are no longer available.

#### 0.5.4.1.1 Handle Removed Assignments

Safely handle Google events whose Canvas assignments were removed.

**End Goal:**

- Removed Canvas assignments do not leave misleading calendar entries.

**Work Steps:**

- [ ] Detect missing Canvas assignments
- [ ] Distinguish removed assignments from API failures
- [ ] Define safe removal behavior
- [ ] Prevent destructive changes when Canvas cannot be reached
- [ ] Remove or mark events only when removal is confirmed

# 0.6 Automatic Synchronization

Run synchronization automatically on a regular schedule.

## 0.6.1 Sync Runner

Create a complete synchronization command.

### 0.6.1.1 Synchronization Workflow

Run all synchronization operations together.

#### 0.6.1.1.1 Run Full Synchronization

Create a single command that synchronizes all courses.

**End Goal:**

- One command completely synchronizes Canvas with Google Calendar.

**Work Steps:**

- [ ] Connect to Canvas
- [ ] Retrieve courses
- [ ] Retrieve assignments
- [ ] Connect to Google Calendar
- [ ] Verify course calendars
- [ ] Create new events
- [ ] Update changed events
- [ ] Handle removed assignments
- [ ] Print a synchronization summary

## 0.6.2 Scheduler

Run synchronization without manual intervention.

### 0.6.2.1 Scheduled Sync

Execute synchronization regularly.

#### 0.6.2.1.1 Run Automatic Sync

Schedule synchronization at a reasonable interval.

**End Goal:**

- Canvas changes reach Google Calendar substantially faster than Google's normal Canvas calendar-feed refresh.

**Work Steps:**

- [ ] Choose the sync interval
- [ ] Configure scheduled execution
- [ ] Prevent overlapping sync runs
- [ ] Record the last successful synchronization
- [ ] Handle temporary Canvas failures
- [ ] Handle temporary Google failures

# 0.7 User Experience

Make the synchronization understandable and easy to manage.

## 0.7.1 Status

Show what synchronization is doing.

### 0.7.1.1 Sync Summary

Provide useful results after each run.

#### 0.7.1.1.1 Display Synchronization Results

Report what changed during synchronization.

**End Goal:**

- The user can quickly tell whether synchronization succeeded and what changed.

**Work Steps:**

- [ ] Show courses checked
- [ ] Show assignments checked
- [ ] Show events added
- [ ] Show events updated
- [ ] Show unchanged events
- [ ] Show removed events
- [ ] Show errors

## 0.7.2 Setup

Make first-time configuration straightforward.

### 0.7.2.1 Setup Assistant

Guide users through configuration.

#### 0.7.2.1.1 Create Setup Workflow

Create an interactive setup process.

**End Goal:**

- A user can configure Canvas and Google Calendar without editing application code.

**Work Steps:**

- [ ] Ask for Canvas URL
- [ ] Configure Canvas authentication
- [ ] Test Canvas connection
- [ ] Configure Google authentication
- [ ] Test Google Calendar connection
- [ ] Display detected courses
- [ ] Create or select course calendars
- [ ] Save configuration

# 0.8 Testing and Reliability

Ensure synchronization is safe and predictable.

## 0.8.1 Canvas Tests

Test Canvas data handling.

### 0.8.1.1 Canvas API Tests

Verify course and assignment processing.

#### 0.8.1.1.1 Test Canvas Data

Test Canvas parsing and filtering.

**End Goal:**

- Canvas data is handled consistently.

**Work Steps:**

- [ ] Test course parsing
- [ ] Test assignment parsing
- [ ] Test due dates
- [ ] Test locked assignments
- [ ] Test assignments without due dates
- [ ] Test authentication errors

## 0.8.2 Google Tests

Test Google Calendar operations.

### 0.8.2.1 Calendar API Tests

Verify event creation and updates.

#### 0.8.2.1.1 Test Calendar Operations

Test synchronization without creating incorrect events.

**End Goal:**

- Google Calendar operations behave predictably.

**Work Steps:**

- [ ] Test calendar creation
- [ ] Test event creation
- [ ] Test duplicate prevention
- [ ] Test event updates
- [ ] Test event removal
- [ ] Test authentication errors

## 0.8.3 Integration Tests

Test complete synchronization.

### 0.8.3.1 End-to-End Sync

Test realistic synchronization scenarios.

#### 0.8.3.1.1 Test Full Synchronization

Verify the complete Canvas-to-Google workflow.

**End Goal:**

- The synchronization process handles realistic Canvas changes correctly.

**Work Steps:**

- [ ] Test a newly published assignment
- [ ] Test a locked future assignment
- [ ] Test a changed due date
- [ ] Test a renamed assignment
- [ ] Test an unchanged assignment
- [ ] Test a removed assignment
- [ ] Test repeated synchronization
- [ ] Confirm no duplicate events are created
- [ ] Confirm failures do not cause destructive changes

# 0.9 Release Preparation

Prepare the project for normal use.

## 0.9.1 Documentation

Document installation, configuration, and operation.

### 0.9.1.1 User Documentation

Explain how to use the application.

#### 0.9.1.1.1 Create README

Document the project.

**End Goal:**

- A new user can understand and set up Canvas Calendar Sync.

**Work Steps:**

- [ ] Explain the project's purpose
- [ ] Document installation
- [ ] Document Canvas token setup
- [ ] Document Google authorization
- [ ] Document course calendars
- [ ] Document automatic synchronization
- [ ] Document troubleshooting

## 0.9.2 Initial Release

Prepare the first usable version.

### 0.9.2.1 Version 1.0

Verify the project is ready for regular use.

#### 0.9.2.1.1 Release Version 1.0

Complete the initial production release.

**End Goal:**

- Canvas Calendar Sync is ready for everyday use.

**Work Steps:**

- [ ] Run the complete test suite
- [ ] Test with real Canvas courses
- [ ] Test with real Google calendars
- [ ] Verify automatic synchronization
- [ ] Verify credentials are not stored in Git
- [ ] Complete documentation
- [ ] Tag version 1.0
