/**
 * 计费设置页面
 *
 * 管理计费偏好、通知设置、付款方式等。
 */

'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

// 组件导入
import { BillingLayout, BillingHeader } from '@/components/billing/billing-layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Hooks导入
import { useBillingData, usePaymentManagement } from '@/store/billing-store';

// 图标导入
import {
  BellIcon,
  CreditCardIcon,
  ShieldCheckIcon,
  EnvelopeIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  GlobeAltIcon,
  CogIcon,
  DocumentTextIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';

const BillingSettings: React.FC = () => {
  const { currentSubscription, billingSummary } = useBillingData();
  const { paymentMethods, actions } = usePaymentManagement();

  const [notificationSettings, setNotificationSettings] = useState({
    emailNotifications: true,
    invoiceEmail: '',
    paymentReminders: true,
    usageAlerts: true,
    lowBalanceAlerts: true,
    subscriptionRenewalAlerts: true,
    marketingEmails: false,
  });

  const [billingPreferences, setBillingPreferences] = useState({
    currency: 'USD',
    timezone: 'UTC',
    autoRenewal: true,
    paperlessInvoices: true,
    defaultPaymentMethod: '',
  });

  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPaymentMethods = async () => {
      try {
        await actions.getPaymentMethods();
      } catch (error) {
        console.error('Failed to fetch payment methods:', error);
      }
    };

    fetchPaymentMethods();
  }, [actions]);

  const handleSaveSettings = async (section: 'notifications' | 'preferences') => {
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      // Mock API call - replace with actual implementation
      await new Promise(resolve => setTimeout(resolve, 1000));

      setSuccessMessage(`${section === 'notifications' ? 'Notification' : 'Billing'} settings saved successfully!`);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      setError('Failed to save settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        damping: 20,
        stiffness: 100,
      },
    },
  };

  return (
    <BillingLayout>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Page Header */}
        <BillingHeader
          title="Billing Settings"
          description="Manage your billing preferences and notification settings"
        />

        {/* Success/Error Messages */}
        {successMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <Alert className="bg-green-50 border-green-200">
              <CheckCircleIcon className="w-4 h-4 text-green-600" />
              <AlertDescription className="text-green-800">
                {successMessage}
              </AlertDescription>
            </Alert>
          </motion.div>
        )}

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <Alert className="bg-red-50 border-red-200">
              <ExclamationTriangleIcon className="w-4 h-4 text-red-600" />
              <AlertDescription className="text-red-800">
                {error}
              </AlertDescription>
            </Alert>
          </motion.div>
        )}

        {/* Settings Tabs */}
        <motion.div variants={itemVariants}>
          <Tabs defaultValue="notifications" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="notifications" className="flex items-center gap-2">
                <BellIcon className="w-4 h-4" />
                Notifications
              </TabsTrigger>
              <TabsTrigger value="billing" className="flex items-center gap-2">
                <CogIcon className="w-4 h-4" />
                Billing Preferences
              </TabsTrigger>
              <TabsTrigger value="payment" className="flex items-center gap-2">
                <CreditCardIcon className="w-4 h-4" />
                Payment Methods
              </TabsTrigger>
            </TabsList>

            {/* Notification Settings */}
            <TabsContent value="notifications" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BellIcon className="w-5 h-5" />
                    Email Notifications
                  </CardTitle>
                  <CardDescription>
                    Choose which billing notifications you'd like to receive
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label className="font-medium">Email Notifications</Label>
                        <p className="text-sm text-gray-600">Receive billing updates via email</p>
                      </div>
                      <Switch
                        checked={notificationSettings.emailNotifications}
                        onCheckedChange={(checked) =>
                          setNotificationSettings(prev => ({ ...prev, emailNotifications: checked }))
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="invoiceEmail">Invoice Email Address</Label>
                      <Input
                        id="invoiceEmail"
                        type="email"
                        placeholder="billing@example.com"
                        value={notificationSettings.invoiceEmail}
                        onChange={(e) =>
                          setNotificationSettings(prev => ({ ...prev, invoiceEmail: e.target.value }))
                        }
                      />
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <h4 className="font-medium">Notification Types</h4>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Payment Reminders</Label>
                        <p className="text-sm text-gray-600">Get notified before payment due dates</p>
                      </div>
                      <Switch
                        checked={notificationSettings.paymentReminders}
                        onCheckedChange={(checked) =>
                          setNotificationSettings(prev => ({ ...prev, paymentReminders: checked }))
                        }
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Usage Alerts</Label>
                        <p className="text-sm text-gray-600">Alert when approaching usage limits</p>
                      </div>
                      <Switch
                        checked={notificationSettings.usageAlerts}
                        onCheckedChange={(checked) =>
                          setNotificationSettings(prev => ({ ...prev, usageAlerts: checked }))
                        }
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Low Balance Alerts</Label>
                        <p className="text-sm text-gray-600">Notify when account balance is low</p>
                      </div>
                      <Switch
                        checked={notificationSettings.lowBalanceAlerts}
                        onCheckedChange={(checked) =>
                          setNotificationSettings(prev => ({ ...prev, lowBalanceAlerts: checked }))
                        }
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Subscription Renewal Alerts</Label>
                        <p className="text-sm text-gray-600">Get notified before subscription renews</p>
                      </div>
                      <Switch
                        checked={notificationSettings.subscriptionRenewalAlerts}
                        onCheckedChange={(checked) =>
                          setNotificationSettings(prev => ({ ...prev, subscriptionRenewalAlerts: checked }))
                        }
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Marketing Emails</Label>
                        <p className="text-sm text-gray-600">Receive promotional offers and updates</p>
                      </div>
                      <Switch
                        checked={notificationSettings.marketingEmails}
                        onCheckedChange={(checked) =>
                          setNotificationSettings(prev => ({ ...prev, marketingEmails: checked }))
                        }
                      />
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <Button
                      onClick={() => handleSaveSettings('notifications')}
                      disabled={loading}
                    >
                      {loading ? 'Saving...' : 'Save Notification Settings'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Billing Preferences */}
            <TabsContent value="billing" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CogIcon className="w-5 h-5" />
                    Billing Preferences
                  </CardTitle>
                  <CardDescription>
                    Configure your billing and currency preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="currency">Currency</Label>
                      <Select
                        value={billingPreferences.currency}
                        onValueChange={(value) =>
                          setBillingPreferences(prev => ({ ...prev, currency: value }))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="USD">USD - US Dollar</SelectItem>
                          <SelectItem value="EUR">EUR - Euro</SelectItem>
                          <SelectItem value="GBP">GBP - British Pound</SelectItem>
                          <SelectItem value="JPY">JPY - Japanese Yen</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="timezone">Timezone</Label>
                      <Select
                        value={billingPreferences.timezone}
                        onValueChange={(value) =>
                          setBillingPreferences(prev => ({ ...prev, timezone: value }))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="UTC">UTC</SelectItem>
                          <SelectItem value="America/New_York">Eastern Time (ET)</SelectItem>
                          <SelectItem value="America/Los_Angeles">Pacific Time (PT)</SelectItem>
                          <SelectItem value="Europe/London">London (GMT)</SelectItem>
                          <SelectItem value="Asia/Tokyo">Tokyo (JST)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <h4 className="font-medium">Billing Options</h4>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Auto-Renewal</Label>
                        <p className="text-sm text-gray-600">Automatically renew subscription</p>
                      </div>
                      <Switch
                        checked={billingPreferences.autoRenewal}
                        onCheckedChange={(checked) =>
                          setBillingPreferences(prev => ({ ...prev, autoRenewal: checked }))
                        }
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="font-medium">Paperless Invoices</Label>
                        <p className="text-sm text-gray-600">Receive invoices electronically</p>
                      </div>
                      <Switch
                        checked={billingPreferences.paperlessInvoices}
                        onCheckedChange={(checked) =>
                          setBillingPreferences(prev => ({ ...prev, paperlessInvoices: checked }))
                        }
                      />
                    </div>
                  </div>

                  {/* Current Subscription Summary */}
                  {currentSubscription && (
                    <>
                      <Separator />
                      <div>
                        <h4 className="font-medium mb-4">Current Subscription</h4>
                        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Plan</span>
                            <span className="font-medium capitalize">{currentSubscription.plan?.type}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Cost</span>
                            <span className="font-medium">
                              {formatCurrency(currentSubscription.unitPrice)}/{currentSubscription.billingCycle}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Next Billing</span>
                            <span className="font-medium">
                              {new Date(currentSubscription.currentPeriodEnd).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </>
                  )}

                  <div className="flex justify-end">
                    <Button
                      onClick={() => handleSaveSettings('preferences')}
                      disabled={loading}
                    >
                      {loading ? 'Saving...' : 'Save Billing Preferences'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Payment Methods */}
            <TabsContent value="payment" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CreditCardIcon className="w-5 h-5" />
                    Payment Methods
                  </CardTitle>
                  <CardDescription>
                    Manage your payment methods and billing information
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex justify-between items-center">
                    <h4 className="font-medium">Your Payment Methods</h4>
                    <Button variant="outline">
                      <CreditCardIcon className="w-4 h-4 mr-2" />
                      Add Payment Method
                    </Button>
                  </div>

                  {paymentMethods && paymentMethods.length > 0 ? (
                    <div className="space-y-4">
                      {paymentMethods.map((method) => (
                        <div
                          key={method.id}
                          className="flex items-center justify-between p-4 border rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                              <CreditCardIcon className="w-5 h-5 text-blue-600" />
                            </div>
                            <div>
                              <div className="font-medium capitalize">
                                {method.brand || method.type}
                              </div>
                              <div className="text-sm text-gray-600">
                                {method.last4 ? `•••• ${method.last4}` : 'Payment Method'}
                              </div>
                            </div>
                            {method.isDefault && (
                              <Badge variant="secondary" className="bg-green-100 text-green-800">
                                Default
                              </Badge>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm">
                              Edit
                            </Button>
                            <Button variant="ghost" size="sm" className="text-red-600">
                              Remove
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <CreditCardIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Payment Methods</h3>
                      <p className="text-gray-600 mb-4">
                        Add a payment method to enable automatic billing
                      </p>
                      <Button>
                        <CreditCardIcon className="w-4 h-4 mr-2" />
                        Add Payment Method
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Security Settings */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ShieldCheckIcon className="w-5 h-5" />
                    Security Settings
                  </CardTitle>
                  <CardDescription>
                    Manage your billing security preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="font-medium">Two-Factor Authentication</Label>
                      <p className="text-sm text-gray-600">Add extra security to billing operations</p>
                    </div>
                    <Button variant="outline" size="sm">
                      Configure 2FA
                    </Button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="font-medium">Billing Permissions</Label>
                      <p className="text-sm text-gray-600">Control who can access billing information</p>
                    </div>
                    <Button variant="outline" size="sm">
                      Manage Access
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      </motion.div>
    </BillingLayout>
  );
};

export default BillingSettings;