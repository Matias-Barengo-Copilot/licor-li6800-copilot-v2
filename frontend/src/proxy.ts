import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  const token = request.cookies.get('token')

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Run proxy on all paths EXCEPT:
     * - /login (the login page itself)
     * - /api/* (these are proxied to FastAPI which has its own JWT middleware)
     * - /_next/* (Next.js internals)
     * - static files
     */
    '/((?!login|api|_next/static|_next/image|favicon.ico).*)',
  ],
}
