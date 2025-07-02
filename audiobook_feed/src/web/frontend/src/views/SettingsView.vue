<template>
  <div class="settings-view">
    <h1 class="text-h4 mb-6">Settings</h1>
    
    <v-tabs v-model="activeTab" color="primary" align-tabs="start">
      <v-tab value="general">General</v-tab>
      <v-tab value="api">API Keys</v-tab>
      <v-tab value="notifications">Notifications</v-tab>
      <v-tab value="appearance">Appearance</v-tab>
    </v-tabs>
    
    <v-window v-model="activeTab" class="mt-4">
      <!-- General Settings -->
      <v-window-item value="general">
        <v-card>
          <v-card-title>General Settings</v-card-title>
          <v-card-text>
            <v-form>
              <v-switch
                v-model="settings.general.autoRefresh"
                label="Auto-refresh feeds"
                hint="Automatically refresh feeds when opening the app"
                persistent-hint
              ></v-switch>
              
              <v-select
                v-model="settings.general.refreshInterval"
                :items="refreshIntervals"
                label="Feed Refresh Interval"
                hint="How often should feeds be checked for updates"
                persistent-hint
                class="mt-4"
              ></v-select>
              
              <v-select
                v-model="settings.general.defaultLanguage"
                :items="languages"
                label="Default Language"
                hint="Preferred language for audiobook results"
                persistent-hint
                class="mt-4"
              ></v-select>
              
              <v-file-input
                v-model="settings.general.exportDirectory"
                label="Export Directory"
                hint="Where to save exported feeds and calendars"
                persistent-hint
                class="mt-4"
                placeholder="Default: Downloads folder"
              ></v-file-input>
            </v-form>
          </v-card-text>
        </v-card>
      </v-window-item>
      
      <!-- API Keys -->
      <v-window-item value="api">
        <v-card>
          <v-card-title>API Keys</v-card-title>
          <v-card-text>
            <v-form>
              <v-text-field
                v-model="settings.api.audibleApiKey"
                label="Audible API Key"
                hint="Optional: For higher rate limits"
                persistent-hint
                type="password"
                append-icon="mdi-eye"
                @click:append="() => {}"
              ></v-text-field>
              
              <v-text-field
                v-model="settings.api.audnexApiKey"
                label="Audnex API Key"
                hint="Optional: For API access to audnex.us"
                persistent-hint
                type="password"
                append-icon="mdi-eye"
                @click:append="() => {}"
                class="mt-4"
              ></v-text-field>
              
              <v-alert
                type="info"
                class="mt-4"
              >
                API keys are stored securely on your device. They are only sent to the respective services when making API requests.
              </v-alert>
            </v-form>
          </v-card-text>
        </v-card>
      </v-window-item>
      
      <!-- Notifications -->
      <v-window-item value="notifications">
        <v-card>
          <v-card-title>Notification Settings</v-card-title>
          <v-card-text>
            <v-form>
              <v-switch
                v-model="settings.notifications.enabled"
                label="Enable Notifications"
                hint="Get notified about new audiobook releases"
                persistent-hint
              ></v-switch>
              
              <div class="mt-4">
                <h3 class="text-h6 mb-2">Notification Channels</h3>
                
                <!-- Email Notifications -->
                <v-expansion-panels>
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <div class="d-flex align-center">
                        <v-icon class="mr-2">mdi-email</v-icon>
                        Email Notifications
                        <v-switch
                          v-model="settings.notifications.email.enabled"
                          class="ml-4"
                          hide-details
                          @click.stop
                        ></v-switch>
                      </div>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-text-field
                        v-model="settings.notifications.email.address"
                        label="Email Address"
                        :disabled="!settings.notifications.email.enabled"
                      ></v-text-field>
                      
                      <v-text-field
                        v-model="settings.notifications.email.smtpServer"
                        label="SMTP Server"
                        :disabled="!settings.notifications.email.enabled"
                      ></v-text-field>
                      
                      <v-text-field
                        v-model="settings.notifications.email.smtpPort"
                        label="SMTP Port"
                        type="number"
                        :disabled="!settings.notifications.email.enabled"
                      ></v-text-field>
                      
                      <v-text-field
                        v-model="settings.notifications.email.smtpUsername"
                        label="SMTP Username"
                        :disabled="!settings.notifications.email.enabled"
                      ></v-text-field>
                      
                      <v-text-field
                        v-model="settings.notifications.email.smtpPassword"
                        label="SMTP Password"
                        type="password"
                        :disabled="!settings.notifications.email.enabled"
                      ></v-text-field>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                  
                  <!-- Pushover Notifications -->
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <div class="d-flex align-center">
                        <v-icon class="mr-2">mdi-cellphone</v-icon>
                        Pushover Notifications
                        <v-switch
                          v-model="settings.notifications.pushover.enabled"
                          class="ml-4"
                          hide-details
                          @click.stop
                        ></v-switch>
                      </div>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-text-field
                        v-model="settings.notifications.pushover.apiKey"
                        label="Pushover API Key"
                        :disabled="!settings.notifications.pushover.enabled"
                      ></v-text-field>
                      
                      <v-text-field
                        v-model="settings.notifications.pushover.userKey"
                        label="Pushover User Key"
                        :disabled="!settings.notifications.pushover.enabled"
                      ></v-text-field>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                  
                  <!-- Discord Notifications -->
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <div class="d-flex align-center">
                        <v-icon class="mr-2">mdi-discord</v-icon>
                        Discord Notifications
                        <v-switch
                          v-model="settings.notifications.discord.enabled"
                          class="ml-4"
                          hide-details
                          @click.stop
                        ></v-switch>
                      </div>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-text-field
                        v-model="settings.notifications.discord.webhookUrl"
                        label="Discord Webhook URL"
                        :disabled="!settings.notifications.discord.enabled"
                      ></v-text-field>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>
              
              <v-select
                v-model="settings.notifications.frequency"
                :items="notificationFrequencies"
                label="Notification Frequency"
                hint="How often to check for new releases"
                persistent-hint
                class="mt-4"
              ></v-select>
            </v-form>
          </v-card-text>
        </v-card>
      </v-window-item>
      
      <!-- Appearance -->
      <v-window-item value="appearance">
        <v-card>
          <v-card-title>Appearance Settings</v-card-title>
          <v-card-text>
            <v-form>
              <v-switch
                v-model="settings.appearance.darkMode"
                label="Dark Mode"
                hint="Enable dark theme for the application"
                persistent-hint
              ></v-switch>
              
              <v-radio-group
                v-model="settings.appearance.colorTheme"
                label="Color Theme"
                class="mt-4"
              >
                <v-radio value="blue" label="Blue"></v-radio>
                <v-radio value="purple" label="Purple"></v-radio>
                <v-radio value="green" label="Green"></v-radio>
                <v-radio value="orange" label="Orange"></v-radio>
              </v-radio-group>
            </v-form>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>
    
    <div class="d-flex justify-end mt-4">
      <v-btn
        color="primary"
        @click="saveSettings"
        :loading="saving"
      >
        Save Settings
      </v-btn>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SettingsView',
  data() {
    return {
      activeTab: 'general',
      saving: false,
      refreshIntervals: [
        { title: 'Every hour', value: 60 },
        { title: 'Every 12 hours', value: 720 },
        { title: 'Daily', value: 1440 },
        { title: 'Weekly', value: 10080 },
        { title: 'Monthly', value: 43200 }
      ],
      languages: [
        { title: 'English', value: 'english' },
        { title: 'Spanish', value: 'spanish' },
        { title: 'French', value: 'french' },
        { title: 'German', value: 'german' }
      ],
      notificationFrequencies: [
        { title: 'Real-time', value: 'realtime' },
        { title: 'Daily', value: 'daily' },
        { title: 'Weekly', value: 'weekly' }
      ],
      settings: {
        general: {
          autoRefresh: true,
          refreshInterval: 1440,
          defaultLanguage: 'english',
          exportDirectory: null
        },
        api: {
          audibleApiKey: '',
          audnexApiKey: ''
        },
        notifications: {
          enabled: true,
          frequency: 'daily',
          email: {
            enabled: false,
            address: '',
            smtpServer: '',
            smtpPort: 587,
            smtpUsername: '',
            smtpPassword: ''
          },
          pushover: {
            enabled: false,
            apiKey: '',
            userKey: ''
          },
          discord: {
            enabled: false,
            webhookUrl: ''
          }
        },
        appearance: {
          darkMode: false,
          colorTheme: 'blue'
        }
      }
    };
  },
  methods: {
    saveSettings() {
      this.saving = true;
      
      // In a real app, this would save to backend
      setTimeout(() => {
        this.saving = false;
        // this.$toast.success('Settings saved successfully');
      }, 1000);
    }
  }
};
</script>
