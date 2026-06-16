/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper:   '#FAFAF8',
        sheet:   '#FFFFFF',
        surface: '#FFFFFF',
        raised:  '#F5F5F4',
        border: {
          DEFAULT: '#EBEBEA',
          strong:  '#D5D5D3',
        },
        text: {
          primary:   '#0D0D0D',
          secondary: '#3A3A3A',
          muted:     '#666666',
          dim:       '#888888',
          ghost:     '#AAAAAA',
          silent:    '#CCCCCA',
        },
        indigo: {
          DEFAULT: '#4F46E5',
          mid:     '#6366F1',
          surface: 'rgba(79,70,229,0.06)',
          border:  'rgba(79,70,229,0.15)',
          glow:    'rgba(79,70,229,0.22)',
        },
        alarm: {
          DEFAULT: '#DC2626',
          surface: 'rgba(220,38,38,0.07)',
          border:  'rgba(220,38,38,0.18)',
        },
        caution: {
          DEFAULT: '#D97706',
          surface: 'rgba(217,119,6,0.08)',
          border:  'rgba(217,119,6,0.18)',
        },
        clear: {
          DEFAULT: '#16A34A',
          surface: 'rgba(22,163,74,0.07)',
          border:  'rgba(22,163,74,0.18)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'display':  ['28px', { lineHeight: '1.15', letterSpacing: '-0.035em', fontWeight: '700' }],
        'title':    ['18px', { lineHeight: '1.3',  letterSpacing: '-0.025em', fontWeight: '700' }],
        'heading':  ['14px', { lineHeight: '1.4',  letterSpacing: '-0.015em', fontWeight: '600' }],
        'body':     ['12px', { lineHeight: '1.5',  letterSpacing: '0.005em',  fontWeight: '400' }],
        'label':    ['11px', { lineHeight: '1.4',  letterSpacing: '0.005em',  fontWeight: '500' }],
        'caption':  ['10px', { lineHeight: '1',    letterSpacing: '0.06em',   fontWeight: '500' }],
        'data-lg':  ['26px', { lineHeight: '1',    letterSpacing: '-0.05em',  fontWeight: '700' }],
        'data-md':  ['14px', { lineHeight: '1',    letterSpacing: '-0.03em',  fontWeight: '600' }],
        'data-sm':  ['10.5px', { lineHeight: '1.4', letterSpacing: '0',       fontWeight: '500' }],
      },
      spacing: {
        'space-1': '4px',
        'space-2': '8px',
        'space-3': '12px',
        'space-4': '16px',
        'space-5': '20px',
        'space-6': '24px',
        'space-8': '32px',
      },
      borderRadius: {
        'r-sm': '4px',
        'r-md': '7px',
        'r-lg': '9px',
        'r-xl': '12px',
      },
    },
  },
  plugins: [],
}
