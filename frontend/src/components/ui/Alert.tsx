import React from 'react';

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'success' | 'error' | 'warning' | 'info';
  title?: string;
}

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      children,
      variant = 'info',
      title,
      className = '',
      ...props
    },
    ref
  ) => {
    const baseClasses = 'rounded-md p-4';
    
    const variantClasses = {
      success: 'bg-green-50 text-green-800 border border-green-200',
      error: 'bg-red-50 text-red-800 border border-red-200',
      warning: 'bg-yellow-50 text-yellow-800 border border-yellow-200',
      info: 'bg-blue-50 text-blue-800 border border-blue-200',
    };
    
    const classes = `${baseClasses} ${variantClasses[variant]} ${className}`;
    
    return (
      <div ref={ref} className={classes} {...props}>
        {title && (
          <h3 className="text-sm font-medium mb-1">
            {title}
          </h3>
        )}
        {children && (
          <div className={`text-sm ${title ? 'mt-1' : ''}`}>
            {children}
          </div>
        )}
      </div>
    );
  }
);

Alert.displayName = 'Alert';