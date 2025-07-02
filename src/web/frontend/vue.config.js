module.exports = {
  devServer: {
    port: 5006,
    proxy: {
      '/api': {
        target: 'http://localhost:5005',
        changeOrigin: true
      }
    }
  },
  // Use relative paths for assets
  publicPath: './',
  // Output dir for production build
  outputDir: 'dist',
  // Source maps for development
  configureWebpack: {
    devtool: 'source-map'
  },
  // Use specific CSS loaders
  css: {
    loaderOptions: {
      css: {
        sourceMap: true
      }
    }
  }
}
