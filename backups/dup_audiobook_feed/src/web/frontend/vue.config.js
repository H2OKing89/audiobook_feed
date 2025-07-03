const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  lintOnSave: false, // This will disable linting during serve to avoid the eslint errors
  devServer: {
    port: 5006 // Use port 5006 instead of the default 8080
  }
});
