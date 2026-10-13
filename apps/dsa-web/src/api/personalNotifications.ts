import apiClient from './index';
import { toCamelCase } from './utils';

export type PersonalNotificationChannel = {
  id: number;
  channel: 'email' | 'feishu' | 'dingtalk' | 'discord' | 'slack';
  label: string;
  destination: string;
  enabled: boolean;
};

export type PersonalScheduledPushTask = {
  id: number;
  name: string;
  scheduleTime: string;
  stockCodes: string[];
  channel: PersonalNotificationChannel['channel'];
  destination: string;
  includeAiAnalysis: boolean;
  includeNewsSummary: boolean;
  enabled: boolean;
  lastRunAt: string | null;
  lastError: string | null;
};

export const personalNotificationsApi = {
  async list(): Promise<PersonalNotificationChannel[]> {
    const response = await apiClient.get<{ channels: PersonalNotificationChannel[] }>('/api/v1/personal/notifications');
    return toCamelCase<{ channels: PersonalNotificationChannel[] }>(response.data).channels;
  },
  async save(input: { channel: PersonalNotificationChannel['channel']; destination: string; label: string; enabled: boolean }): Promise<PersonalNotificationChannel> {
    const response = await apiClient.put<PersonalNotificationChannel>('/api/v1/personal/notifications', input);
    return toCamelCase<PersonalNotificationChannel>(response.data);
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/api/v1/personal/notifications/${id}`);
  },
  async listScheduled(): Promise<PersonalScheduledPushTask[]> {
    const response = await apiClient.get<{ tasks: PersonalScheduledPushTask[] }>('/api/v1/personal/notifications/scheduled');
    return toCamelCase<{ tasks: PersonalScheduledPushTask[] }>(response.data).tasks;
  },
  async saveScheduled(input: {
    id?: number;
    name: string;
    scheduleTime: string;
    stockCodes: string[];
    channel: PersonalNotificationChannel['channel'];
    destination: string;
    includeAiAnalysis: boolean;
    includeNewsSummary: boolean;
    enabled: boolean;
  }): Promise<PersonalScheduledPushTask> {
    const response = await apiClient.put<PersonalScheduledPushTask>('/api/v1/personal/notifications/scheduled', {
      id: input.id,
      name: input.name,
      schedule_time: input.scheduleTime,
      stock_codes: input.stockCodes,
      channel: input.channel,
      destination: input.destination,
      include_ai_analysis: input.includeAiAnalysis,
      include_news_summary: input.includeNewsSummary,
      enabled: input.enabled,
    });
    return toCamelCase<PersonalScheduledPushTask>(response.data);
  },
  async removeScheduled(id: number): Promise<void> {
    await apiClient.delete(`/api/v1/personal/notifications/scheduled/${id}`);
  },
};
