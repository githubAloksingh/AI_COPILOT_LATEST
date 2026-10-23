-- V28: Add wireframe, explanation, and interaction model support for Mock Screens
ALTER TABLE mock_screen ADD COLUMN wireframe_data LONGBLOB NULL AFTER image_data;
ALTER TABLE mock_screen ADD COLUMN wireframe_path VARCHAR(1024) NULL AFTER wireframe_data;
ALTER TABLE mock_screen ADD COLUMN explanation_json LONGTEXT NULL AFTER specification_json;
ALTER TABLE mock_screen_generation ADD COLUMN interaction_model_json LONGTEXT NULL AFTER screen_plan_json;
