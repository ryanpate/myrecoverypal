#!/usr/bin/env ruby
require 'xcodeproj'

project_path = File.join(__dir__, '..', 'ios', 'App', 'App.xcodeproj')
project = Xcodeproj::Project.open(project_path)

# Remove existing target if present (for re-running after path fix)
existing_target = project.targets.find { |t| t.name == 'SobrietyCounterWidget' }
if existing_target
  puts "Removing existing SobrietyCounterWidget target for re-creation..."
  existing_target.build_phases.each(&:remove_from_project)
  existing_target.dependencies.each(&:remove_from_project)
  existing_target.build_configurations.each(&:remove_from_project)
  existing_target.remove_from_project

  # Remove existing widget file group
  existing_group = project.main_group.children.find { |g| g.display_name == 'SobrietyCounterWidget' }
  existing_group.remove_from_project if existing_group

  # Remove embed phase from app target
  app_t = project.targets.find { |t| t.name == 'App' }
  if app_t
    app_t.build_phases.select { |p|
      p.is_a?(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase) && p.name == 'Embed App Extensions'
    }.each(&:remove_from_project)
    # Remove widget dependency
    app_t.dependencies.select { |d| d.target&.name == 'SobrietyCounterWidget' rescue false }.each(&:remove_from_project)
  end
end

# Create the widget extension target
widget_target = project.new_target(
  :app_extension,
  'SobrietyCounterWidget',
  :ios,
  '14.0'
)

# Set bundle identifier and build settings for all configs
widget_target.build_configurations.each do |config|
  config.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = 'com.myrecoverypal.app.SobrietyCounterWidget'
  config.build_settings['SWIFT_VERSION'] = '5.0'
  config.build_settings['INFOPLIST_FILE'] = 'SobrietyCounterWidget/Info.plist'
  config.build_settings['CODE_SIGN_ENTITLEMENTS'] = 'SobrietyCounterWidget/SobrietyCounterWidget.entitlements'
  config.build_settings['ASSETCATALOG_COMPILER_WIDGET_BACKGROUND_COLOR_NAME'] = 'WidgetBackground'
  config.build_settings['TARGETED_DEVICE_FAMILY'] = '1,2'
  config.build_settings['MARKETING_VERSION'] = '1.0.0'
  config.build_settings['CURRENT_PROJECT_VERSION'] = '1'
  config.build_settings['GENERATE_INFOPLIST_FILE'] = 'NO'
  config.build_settings['PRODUCT_NAME'] = '$(TARGET_NAME)'
  config.build_settings['LD_RUNPATH_SEARCH_PATHS'] = [
    '$(inherited)',
    '@executable_path/Frameworks',
    '@executable_path/../../Frameworks'
  ]
end

# Create file group
widget_group = project.main_group.new_group('SobrietyCounterWidget', 'SobrietyCounterWidget')

# Add source files (paths relative to group, which already has SobrietyCounterWidget path)
swift_files = [
  'SobrietyCounterWidget.swift',
  'SobrietyCounterWidgetViews.swift'
]

swift_files.each do |filename|
  file_ref = widget_group.new_file(filename)
  widget_target.source_build_phase.add_file_reference(file_ref)
end

# Add Info.plist and entitlements as file references (not in build phase)
widget_group.new_file('Info.plist')
widget_group.new_file('SobrietyCounterWidget.entitlements')

# Embed the widget extension in the main app
app_target = project.targets.find { |t| t.name == 'App' }
if app_target
  # Add embed extension build phase if it doesn't exist
  embed_phase = app_target.build_phases.find { |p| p.is_a?(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase) && p.symbol_dst_subfolder_spec == :plug_ins }

  unless embed_phase
    embed_phase = project.new(Xcodeproj::Project::Object::PBXCopyFilesBuildPhase)
    embed_phase.name = 'Embed App Extensions'
    embed_phase.symbol_dst_subfolder_spec = :plug_ins
    app_target.build_phases << embed_phase
  end

  # Add widget product to embed phase
  build_file = embed_phase.add_file_reference(widget_target.product_reference)
  build_file.settings = { 'ATTRIBUTES' => ['RemoveHeadersOnCopy'] }

  # Add target dependency
  app_target.add_dependency(widget_target)
end

# Also add WidgetBridge.swift and MyViewController.swift to the main App target's source build phase
# if they aren't already there
app_group = project.main_group.find_subpath('App', false)
if app_group
  ['WidgetBridge.swift', 'MyViewController.swift'].each do |filename|
    # Check if file reference already exists
    existing = app_group.files.find { |f| f.path == filename }
    unless existing
      file_ref = app_group.new_file(filename)
      app_target.source_build_phase.add_file_reference(file_ref) if app_target
    end
  end
end

project.save

puts "Successfully added SobrietyCounterWidget extension target."
puts "Bundle ID: com.myrecoverypal.app.SobrietyCounterWidget"
puts "Deployment target: iOS 14.0"
