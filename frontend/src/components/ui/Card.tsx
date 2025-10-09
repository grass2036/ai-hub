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
    const baseClasses = 'bg-white shadow-sm hover:shadow-md transition-all duration-300 border border-gray-100 rounded-xl overflow-hidden backdrop-blur-sm bg-white/95';
    const classes = `${baseClasses} ${className}`;

    return (
      <div
        ref={ref}
        className={classes}
        {...props}
        style={{
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)'
        }}
      >
        {(title || subtitle || actions) && (
          <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
              <div className="min-w-0 flex-1">
                {title && (
                  <h3 className="text-lg font-semibold text-gray-900 truncate">{title}</h3>
                )}
                {subtitle && (
                  <p className="mt-1 text-sm text-gray-600 break-words">{subtitle}</p>
                )}
              </div>
              {actions && (
                <div className="flex-shrink-0">
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