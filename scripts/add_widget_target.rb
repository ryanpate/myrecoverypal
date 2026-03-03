#!/usr/bin/env ruby
require 'xcodeproj'

project_path = File.join(__dir__, '..', 'ios', 'App', 'App.xcodeproj')
project = Xcodeproj::Project.open(project_path)

# Check if target already exists
if project.targets.any? { |t| t.name == 'SobrietyCounterWidget' }
  puts "Target 'SobrietyCounterWidget' already exists. Skipping."
  exit 0
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

# Add source files
swift_files = [
  'SobrietyCounterWidget/SobrietyCounterWidget.swift',
  'SobrietyCounterWidget/SobrietyCounterWidgetViews.swift'
]

swift_files.each do |path|
  file_ref = widget_group.new_file(path)
  widget_target.source_build_phase.add_file_reference(file_ref)
end

# Add Info.plist and entitlements as file references (not in build phase)
widget_group.new_file('SobrietyCounterWidget/Info.plist')
widget_group.new_file('SobrietyCounterWidget/SobrietyCounterWidget.entitlements')

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
  ['App/WidgetBridge.swift', 'App/MyViewController.swift'].each do |path|
    # Check if file reference already exists
    existing = app_group.files.find { |f| f.path == File.basename(path) }
    unless existing
      file_ref = app_group.new_file(path)
      app_target.source_build_phase.add_file_reference(file_ref) if app_target
    end
  end
end

project.save

puts "Successfully added SobrietyCounterWidget extension target."
puts "Bundle ID: com.myrecoverypal.app.SobrietyCounterWidget"
puts "Deployment target: iOS 14.0"
