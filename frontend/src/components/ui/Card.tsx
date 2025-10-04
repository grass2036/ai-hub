import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      title,
      subtitle,
      actions,
      className = '',
      ...props
    },
    ref
  ) => {
    const baseClasses = 'bg-white shadow rounded-lg overflow-hidden';
    const classes = `${baseClasses} ${className}`;
    
    return (
      <div ref={ref} className={classes} {...props}>
        {(title || subtitle || actions) && (
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex justify-between items-start">
              <div>
                {title && (
                  <h3 className="text-lg font-medium text-gray-900">{title}</h3>
                )}
                {subtitle && (
                  <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
                )}
              </div>
              {actions && (
                <div className="ml-4 flex-shrink-0">
                  {actions}
                </div>
              )}
            </div>
          </div>
        )}
        <div className="px-6 py-4">
          {children}
        </div>
      </div>
    );
  }
);

Card.displayName = 'Card';